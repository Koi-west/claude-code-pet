import React, { useMemo, useState } from 'react';
import { Skill, SkillCard } from './SkillCard';
import { cacheManager, CACHE_KEYS, CACHE_DURATION } from '../../utils/cache';
import { LayoutGrid, Code, Sparkles, Cog, Wrench } from 'lucide-react';

interface SkillsListProps {
  skills: Skill[];
  onSkillSelect: (skill: Skill) => void;
  onSkillInstall: (skill: Skill) => void;
  onSkillUninstall: (skill: Skill) => void;
}

export function SkillsList({
  skills,
  onSkillSelect,
  onSkillInstall,
  onSkillUninstall,
}: SkillsListProps) {
  const [filter, setFilter] = useState<'all' | 'development' | 'productivity' | 'automation' | 'utility'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const categories = [
    { id: 'all', name: 'All Skills', icon: LayoutGrid },
    { id: 'development', name: 'Development', icon: Code },
    { id: 'productivity', name: 'Productivity', icon: Sparkles },
    { id: 'automation', name: 'Automation', icon: Cog },
    { id: 'utility', name: 'Utility', icon: Wrench },
  ];

  const filteredSkills = useMemo(() => {
    const cacheKey = CACHE_KEYS.SKILLS_SEARCH(`${filter}:${searchQuery.toLowerCase()}`);
    const cached = cacheManager.get<Skill[]>(cacheKey, CACHE_DURATION.SKILLS_SEARCH);
    if (cached) {
      return cached;
    }

    const result = skills.filter((skill) => {
      const matchesCategory = filter === 'all' || skill.category === filter;
      const matchesSearch = !searchQuery ||
        skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        skill.description.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    });

    cacheManager.set(cacheKey, result, CACHE_DURATION.SKILLS_SEARCH);
    return result;
  }, [skills, filter, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Search and Filter */}
      <div className="space-y-4">
        <div className="relative">
          <input
            type="text"
            placeholder="Search skills..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          <svg
            className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-neutral-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>

        <div className="flex gap-2 overflow-x-auto">
          {categories.map((category) => (
            <button
              key={category.id}
              onClick={() => setFilter(category.id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                filter === category.id
                  ? 'bg-primary-500 text-white'
                  : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
              }`}
            >
              <category.icon className="w-4 h-4" />
              {category.name}
            </button>
          ))}
        </div>
      </div>

      {/* Skills Grid */}
      {filteredSkills.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredSkills.map((skill) => (
            <SkillCard
              key={skill.id}
              skill={skill}
              onSelect={onSkillSelect}
              onInstall={onSkillInstall}
              onUninstall={onSkillUninstall}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <div className="text-neutral-400 mb-4">
            <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-neutral-900 mb-2">No skills found</h3>
          <p className="text-neutral-600">Try adjusting your search or filter criteria</p>
        </div>
      )}
    </div>
  );
}
