const path = require('path');

const rootDir = path.resolve(__dirname, '..');

module.exports = {
  // Root directories
  root: rootDir,
  src: path.resolve(rootDir, 'src'),
  dist: path.resolve(rootDir, 'dist'),
  public: path.resolve(rootDir, 'public'),
  config: path.resolve(rootDir, 'config'),

  // Source directories
  main: path.resolve(rootDir, 'src/main'),
  renderer: path.resolve(rootDir, 'src/renderer'),
  core: path.resolve(rootDir, 'src/core'),
  types: path.resolve(rootDir, 'src/types'),
  utils: path.resolve(rootDir, 'src/utils'),

  // Renderer subdirectories
  rendererPet: path.resolve(rootDir, 'src/renderer/pet'),
  rendererDashboard: path.resolve(rootDir, 'src/renderer/dashboard'),
  rendererShared: path.resolve(rootDir, 'src/renderer/shared'),

  // Output directories
  distMain: path.resolve(rootDir, 'dist/main'),
  distRenderer: path.resolve(rootDir, 'dist/renderer'),
  distPublic: path.resolve(rootDir, 'dist/public'),

  // Public subdirectories
  publicPet: path.resolve(rootDir, 'public/pet'),
  publicDashboard: path.resolve(rootDir, 'public/dashboard'),
  publicAssets: path.resolve(rootDir, 'public/assets'),

  // Entry points
  mainEntry: path.resolve(rootDir, 'src/main/index.ts'),
  petEntry: path.resolve(rootDir, 'src/renderer/pet/index.tsx'),
  dashboardEntry: path.resolve(rootDir, 'src/renderer/dashboard/index.tsx'),

  // HTML templates
  petTemplate: path.resolve(rootDir, 'public/pet/index.html'),
  dashboardTemplate: path.resolve(rootDir, 'public/dashboard/index.html'),

  // Assets
  assets: path.resolve(rootDir, 'assets'),

  // Node modules
  nodeModules: path.resolve(rootDir, 'node_modules'),
};
