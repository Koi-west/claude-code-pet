interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

class CacheManager {
  private cache = new Map<string, CacheEntry<any>>();

  set<T>(key: string, data: T, ttl: number = 300000): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
    });

    // Auto-expire after TTL
    setTimeout(() => {
      this.delete(key);
    }, ttl);
  }

  get<T>(key: string, ttl: number = 300000): T | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    const isExpired = Date.now() - entry.timestamp > ttl;
    if (isExpired) {
      this.delete(key);
      return null;
    }

    return entry.data as T;
  }

  delete(key: string): void {
    this.cache.delete(key);
  }

  clear(): void {
    this.cache.clear();
  }

  has(key: string): boolean {
    return this.cache.has(key);
  }
}

export const cacheManager = new CacheManager();

// Cache keys
export const CACHE_KEYS = {
  SKILLS: 'skills',
  SKILLS_SEARCH: (query: string) => `skills_search_${query}`,
};

// Cache durations (in milliseconds)
export const CACHE_DURATION = {
  SKILLS: 300000, // 5 minutes
  SKILLS_SEARCH: 120000, // 2 minutes
};
