import fs from 'fs';
import path from 'path';
import os from 'os';
import type {
  CloudCodeConnection,
  CloudCodeMcpConfig,
  CloudCodeMcpServer,
  CloudCodePlugin,
  CloudCodeSnapshot,
  CloudCodeSkill,
} from '@types';

type SettingsSource = 'project' | 'home';

const CLAUDE_DIR_NAME = '.claude';
const SKILLS_DIR_NAME = 'skills';
const PLUGINS_DIR_NAME = 'plugins';
const SETTINGS_FILE = 'settings.json';
const SETTINGS_LOCAL_FILE = 'settings.local.json';
const MCP_FILE = 'mcp.json';

const HIDDEN_DIR_PREFIX = '.';

type JsonReadResult<T> = { data: T | null; error?: string };

function readJsonFile<T>(filePath: string): JsonReadResult<T> {
  try {
    if (!fs.existsSync(filePath)) {
      return { data: null };
    }
    const raw = fs.readFileSync(filePath, 'utf-8');
    return { data: JSON.parse(raw) as T };
  } catch (error) {
    return { data: null, error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

function readTextFile(filePath: string): JsonReadResult<string> {
  try {
    if (!fs.existsSync(filePath)) {
      return { data: null };
    }
    return { data: fs.readFileSync(filePath, 'utf-8') };
  } catch (error) {
    return { data: null, error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

function resolveClaudeFile(projectPath: string, fileName: string): { path: string; source: SettingsSource; exists: boolean } {
  const projectFile = path.join(projectPath, CLAUDE_DIR_NAME, fileName);
  if (fs.existsSync(projectFile)) {
    return { path: projectFile, source: 'project', exists: true };
  }
  const homeFile = path.join(os.homedir(), CLAUDE_DIR_NAME, fileName);
  return { path: homeFile, source: 'home', exists: fs.existsSync(homeFile) };
}

function getHomeClaudeDir(): string {
  return path.join(os.homedir(), CLAUDE_DIR_NAME);
}

function normalizeEnvValue(value: unknown): string {
  if (typeof value === 'string') return value;
  if (value === null || value === undefined) return '';
  return String(value);
}

function parseEnvLines(raw: string): { env: Record<string, string>; errors: string[] } {
  const env: Record<string, string> = {};
  const errors: string[] = [];
  const lines = raw.split(/\r?\n/);

  lines.forEach((line, index) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) return;

    const normalized = trimmed.startsWith('export ') ? trimmed.slice(7).trim() : trimmed;
    const separatorIndex = normalized.indexOf('=');
    if (separatorIndex <= 0) {
      errors.push(`Line ${index + 1}: Missing "="`);
      return;
    }

    const key = normalized.slice(0, separatorIndex).trim();
    let value = normalized.slice(separatorIndex + 1).trim();

    if (!key) {
      errors.push(`Line ${index + 1}: Empty key`);
      return;
    }

    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }

    env[key] = value;
  });

  return { env, errors };
}

function parseSkillFrontmatter(content: string): { name?: string; description?: string } {
  const lines = content.split(/\r?\n/);
  if (lines[0]?.trim() !== '---') {
    return {};
  }

  const data: Record<string, string> = {};
  for (let i = 1; i < lines.length; i += 1) {
    const line = lines[i];
    if (line.trim() === '---') {
      break;
    }
    const match = line.match(/^([A-Za-z0-9_-]+)\s*:\s*(.*)$/);
    if (match) {
      const key = match[1];
      let value = match[2].trim();
      if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
        value = value.slice(1, -1);
      }
      data[key] = value;
    }
  }

  return {
    name: data.name,
    description: data.description,
  };
}

function pickSkillFile(entries: fs.Dirent[], dirPath: string): string | null {
  const skillFile = entries.find((entry) => entry.isFile() && entry.name === 'SKILL.md');
  if (skillFile) {
    return path.join(dirPath, skillFile.name);
  }
  const fallback = entries.find((entry) => entry.isFile() && entry.name.toLowerCase().endsWith('.md'));
  return fallback ? path.join(dirPath, fallback.name) : null;
}

function collectSkillsInDirectory(rootDir: string, baseDir: string): CloudCodeSkill[] {
  if (!fs.existsSync(rootDir)) {
    return [];
  }

  const skills: CloudCodeSkill[] = [];
  const entries = fs.readdirSync(rootDir, { withFileTypes: true });
  const skillFile = pickSkillFile(entries, rootDir);

  if (skillFile) {
    const { data: content } = readTextFile(skillFile);
    if (content) {
      const meta = parseSkillFrontmatter(content);
      const name = meta.name?.trim();
      const description = meta.description?.trim();
      if (name) {
        const relativeId = path.relative(baseDir, rootDir).split(path.sep).join('/');
        skills.push({
          id: relativeId || name,
          name,
          description,
          path: rootDir,
          file: skillFile,
          source: 'user',
        });
      }
    }
    return skills;
  }

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    if (entry.name.startsWith(HIDDEN_DIR_PREFIX)) continue;
    const nextDir = path.join(rootDir, entry.name);
    skills.push(...collectSkillsInDirectory(nextDir, baseDir));
  }

  return skills;
}

function loadSkills(): CloudCodeSkill[] {
  const skillsDir = path.join(getHomeClaudeDir(), SKILLS_DIR_NAME);
  const skills = collectSkillsInDirectory(skillsDir, skillsDir);
  return skills.sort((a, b) => a.name.localeCompare(b.name));
}

type InstalledPluginEntry = {
  installPath: string;
  version: string;
  installedAt: string;
  lastUpdated?: string;
  scope?: 'user' | 'project' | 'local';
  projectPath?: string;
};

type InstalledPluginsFile = {
  version: number;
  plugins: Record<string, InstalledPluginEntry[]>;
};

type PluginManifest = {
  name?: string;
  description?: string;
  version?: string;
  author?: { name?: string };
};

type MarketplaceManifest = {
  name?: string;
  owner?: { name?: string };
  metadata?: { description?: string; version?: string };
  plugins?: Array<{ name?: string; description?: string; version?: string }>;
};

function pickLatestPluginEntry(entries: InstalledPluginEntry[]): InstalledPluginEntry | null {
  if (!entries.length) return null;
  return entries.reduce((latest, current) => {
    const latestDate = latest.lastUpdated ?? latest.installedAt;
    const currentDate = current.lastUpdated ?? current.installedAt;
    if (currentDate > latestDate) return current;
    if (currentDate < latestDate) return latest;
    return current;
  });
}

function loadPluginMetadata(
  installPath: string,
  pluginId: string
): { name: string; description?: string; version?: string; author?: string; manifestPath?: string; status: CloudCodePlugin['status'] } {
  if (!fs.existsSync(installPath)) {
    return { name: pluginId, status: 'unavailable' };
  }

  const pluginDir = path.join(installPath, '.claude-plugin');
  const pluginManifestPath = path.join(pluginDir, 'plugin.json');
  const marketplaceManifestPath = path.join(pluginDir, 'marketplace.json');

  if (fs.existsSync(pluginManifestPath)) {
    const { data, error } = readJsonFile<PluginManifest>(pluginManifestPath);
    if (data) {
      return {
        name: data.name ?? pluginId,
        description: data.description,
        version: data.version,
        author: data.author?.name,
        manifestPath: pluginManifestPath,
        status: 'available',
      };
    }
    return { name: pluginId, status: 'invalid', manifestPath: pluginManifestPath };
  }

  if (fs.existsSync(marketplaceManifestPath)) {
    const { data } = readJsonFile<MarketplaceManifest>(marketplaceManifestPath);
    const pluginName = pluginId.split('@')[0] || pluginId;
    const marketplacePlugin = data?.plugins?.find((plugin) => plugin?.name === pluginName);
    if (data) {
      return {
        name: marketplacePlugin?.name ?? pluginName,
        description: marketplacePlugin?.description ?? data.metadata?.description,
        version: marketplacePlugin?.version ?? data.metadata?.version,
        author: data.owner?.name,
        manifestPath: marketplaceManifestPath,
        status: 'available',
      };
    }
    return { name: pluginId, status: 'invalid', manifestPath: marketplaceManifestPath };
  }

  return { name: pluginId, status: 'invalid' };
}

function loadEnabledPlugins(settingsLocalPath: string): Record<string, boolean> {
  const { data } = readJsonFile<Record<string, unknown>>(settingsLocalPath);
  if (!data) return {};
  const enabledPlugins = data.enabledPlugins;
  if (!enabledPlugins || typeof enabledPlugins !== 'object') return {};
  const result: Record<string, boolean> = {};
  for (const [key, value] of Object.entries(enabledPlugins as Record<string, unknown>)) {
    if (typeof value === 'boolean') {
      result[key] = value;
    }
  }
  return result;
}

function loadPlugins(projectPath: string): { plugins: CloudCodePlugin[]; settingsLocalPath: string; settingsLocalSource: SettingsSource } {
  const pluginsFile = path.join(getHomeClaudeDir(), PLUGINS_DIR_NAME, 'installed_plugins.json');
  const { data } = readJsonFile<InstalledPluginsFile>(pluginsFile);
  const { path: settingsLocalPath, source: settingsLocalSource } = resolveClaudeFile(projectPath, SETTINGS_LOCAL_FILE);
  const enabledPlugins = loadEnabledPlugins(settingsLocalPath);

  if (!data?.plugins) {
    return { plugins: [], settingsLocalPath, settingsLocalSource };
  }

  const plugins: CloudCodePlugin[] = [];
  for (const [pluginId, entries] of Object.entries(data.plugins)) {
    const latest = pickLatestPluginEntry(entries);
    if (!latest) continue;
    const meta = loadPluginMetadata(latest.installPath, pluginId);
    plugins.push({
      id: pluginId,
      name: meta.name,
      description: meta.description,
      version: meta.version ?? latest.version,
      author: meta.author,
      scope: latest.scope ?? 'user',
      enabled: enabledPlugins[pluginId] ?? false,
      status: meta.status,
      installPath: latest.installPath,
      manifestPath: meta.manifestPath,
    });
  }

  return {
    plugins: plugins.sort((a, b) => a.name.localeCompare(b.name)),
    settingsLocalPath,
    settingsLocalSource,
  };
}

function buildMcpServerSummary(config: Record<string, unknown>): { type: CloudCodeMcpServer['type']; summary: string } {
  const type = typeof config.type === 'string' ? config.type : undefined;
  if (type === 'sse') {
    return { type: 'sse', summary: normalizeEnvValue(config.url) };
  }
  if (type === 'http') {
    return { type: 'http', summary: normalizeEnvValue(config.url) };
  }
  if (typeof config.command === 'string') {
    const args = Array.isArray(config.args) ? config.args.map((arg) => String(arg)) : [];
    const preview = [config.command, ...args].join(' ');
    return { type: 'stdio', summary: preview.trim() };
  }
  if (typeof config.url === 'string') {
    return { type: 'http', summary: config.url };
  }
  return { type: 'unknown', summary: 'Custom config' };
}

function loadMcpConfig(projectPath: string): CloudCodeMcpConfig {
  const mcpPath = path.join(projectPath, CLAUDE_DIR_NAME, MCP_FILE);
  const { data, error } = readJsonFile<Record<string, unknown>>(mcpPath);
  if (!data) {
    return {
      path: mcpPath,
      exists: fs.existsSync(mcpPath),
      raw: null,
      servers: [],
      error,
    };
  }

  const servers: CloudCodeMcpServer[] = [];
  const mcpServers = data.mcpServers;
  if (mcpServers && typeof mcpServers === 'object') {
    for (const [name, config] of Object.entries(mcpServers as Record<string, unknown>)) {
      if (!config || typeof config !== 'object') continue;
      const summary = buildMcpServerSummary(config as Record<string, unknown>);
      servers.push({
        name,
        type: summary.type,
        summary: summary.summary,
        config: config as Record<string, unknown>,
      });
    }
  }

  const { data: raw } = readTextFile(mcpPath);

  return {
    path: mcpPath,
    exists: true,
    raw: raw ?? null,
    servers: servers.sort((a, b) => a.name.localeCompare(b.name)),
  };
}

function loadConnection(projectPath: string): CloudCodeConnection {
  const resolved = resolveClaudeFile(projectPath, SETTINGS_FILE);
  const { data } = readJsonFile<Record<string, unknown>>(resolved.path);

  const env = (data?.env && typeof data.env === 'object') ? data.env as Record<string, unknown> : {};
  const baseUrl = normalizeEnvValue(env.ANTHROPIC_BASE_URL);
  const authToken = normalizeEnvValue(env.ANTHROPIC_AUTH_TOKEN || env.ANTHROPIC_API_KEY);
  const timeoutMs = normalizeEnvValue(env.API_TIMEOUT_MS);

  return {
    settingsPath: resolved.path,
    source: resolved.source,
    baseUrl,
    authToken,
    timeoutMs,
    env: Object.fromEntries(Object.entries(env).map(([key, value]) => [key, normalizeEnvValue(value)])),
  };
}

export function loadCloudCodeSnapshot(projectPath: string): CloudCodeSnapshot {
  const connection = loadConnection(projectPath);
  const skills = loadSkills();
  const pluginsResult = loadPlugins(projectPath);
  const mcp = loadMcpConfig(projectPath);

  return {
    projectPath,
    connection,
    skills,
    plugins: pluginsResult.plugins,
    mcp,
    skillsPath: path.join(getHomeClaudeDir(), SKILLS_DIR_NAME),
    pluginsPath: path.join(getHomeClaudeDir(), PLUGINS_DIR_NAME),
    settingsLocalPath: pluginsResult.settingsLocalPath,
    settingsLocalSource: pluginsResult.settingsLocalSource,
  };
}

export function saveCloudCodeConnection(projectPath: string, updates: { baseUrl: string; authToken: string; timeoutMs: string }): CloudCodeConnection {
  const resolved = resolveClaudeFile(projectPath, SETTINGS_FILE);
  const { data } = readJsonFile<Record<string, unknown>>(resolved.path);
  const next = data && typeof data === 'object' ? { ...data } : {};

  const env = next.env && typeof next.env === 'object' ? { ...(next.env as Record<string, unknown>) } : {};

  if (updates.baseUrl.trim()) {
    env.ANTHROPIC_BASE_URL = updates.baseUrl.trim();
  } else {
    delete env.ANTHROPIC_BASE_URL;
  }

  if (updates.authToken.trim()) {
    env.ANTHROPIC_AUTH_TOKEN = updates.authToken.trim();
    delete env.ANTHROPIC_API_KEY;
  } else {
    delete env.ANTHROPIC_AUTH_TOKEN;
  }

  if (updates.timeoutMs.trim()) {
    env.API_TIMEOUT_MS = updates.timeoutMs.trim();
  } else {
    delete env.API_TIMEOUT_MS;
  }

  next.env = env;

  fs.mkdirSync(path.dirname(resolved.path), { recursive: true });
  fs.writeFileSync(resolved.path, JSON.stringify(next, null, 2));

  return loadConnection(projectPath);
}

export function saveCloudCodeEnv(projectPath: string, envLines: string): CloudCodeConnection {
  const resolved = resolveClaudeFile(projectPath, SETTINGS_FILE);
  const { data } = readJsonFile<Record<string, unknown>>(resolved.path);
  const next = data && typeof data === 'object' ? { ...data } : {};

  const parsed = parseEnvLines(envLines);
  if (parsed.errors.length > 0) {
    throw new Error(parsed.errors.join('; '));
  }

  next.env = parsed.env;

  fs.mkdirSync(path.dirname(resolved.path), { recursive: true });
  fs.writeFileSync(resolved.path, JSON.stringify(next, null, 2));

  return loadConnection(projectPath);
}

export function setCloudCodePluginEnabled(
  projectPath: string,
  pluginId: string,
  enabled: boolean
): { success: boolean; settingsLocalPath: string; error?: string } {
  const resolved = resolveClaudeFile(projectPath, SETTINGS_LOCAL_FILE);
  const { data } = readJsonFile<Record<string, unknown>>(resolved.path);
  const next = data && typeof data === 'object' ? { ...data } : {};
  const enabledPlugins = next.enabledPlugins && typeof next.enabledPlugins === 'object'
    ? { ...(next.enabledPlugins as Record<string, unknown>) }
    : {};

  enabledPlugins[pluginId] = enabled;
  next.enabledPlugins = enabledPlugins;

  try {
    fs.mkdirSync(path.dirname(resolved.path), { recursive: true });
    fs.writeFileSync(resolved.path, JSON.stringify(next, null, 2));
    return { success: true, settingsLocalPath: resolved.path };
  } catch (error) {
    return {
      success: false,
      settingsLocalPath: resolved.path,
      error: error instanceof Error ? error.message : 'Failed to update plugins',
    };
  }
}

export function saveCloudCodeMcpConfig(projectPath: string, raw: string): { success: boolean; error?: string } {
  const mcpPath = path.join(projectPath, CLAUDE_DIR_NAME, MCP_FILE);
  try {
    const parsed = JSON.parse(raw);
    fs.mkdirSync(path.dirname(mcpPath), { recursive: true });
    fs.writeFileSync(mcpPath, JSON.stringify(parsed, null, 2));
    return { success: true };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Invalid MCP JSON',
    };
  }
}
