import React from 'react';
import { Card, CardContent, CardFooter } from '@renderer/shared/components';
import { Badge } from '@renderer/shared/components';
import { Button } from '@renderer/shared/components';
import { ArrowRight, Code, Zap, Database, Star } from 'lucide-react';

export interface Skill {
  id: string;
  name: string;
  description: string;
  category: 'development' | 'productivity' | 'automation' | 'utility';
  version: string;
  author: string;
  rating: number;
  downloads: number;
  isInstalled: boolean;
  isFeatured: boolean;
}

interface SkillCardProps {
  skill: Skill;
  onSelect: (skill: Skill) => void;
  onInstall: (skill: Skill) => void;
  onUninstall: (skill: Skill) => void;
}

export function SkillCard({ skill, onSelect, onInstall, onUninstall }: SkillCardProps) {
  const categoryIcons = {
    development: Code,
    productivity: Zap,
    automation: Database,
    utility: ArrowRight,
  };

  const CategoryIcon = categoryIcons[skill.category];

  return (
    <Card
      className="overflow-hidden transition-all hover:shadow-md hover:-translate-y-1 cursor-pointer"
      onClick={() => onSelect(skill)}
    >
      <CardContent className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-100 rounded-lg">
              <CategoryIcon className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <h3 className="font-semibold text-neutral-900">{skill.name}</h3>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="outline" size="sm">
                  {skill.category}
                </Badge>
                {skill.isFeatured && (
                  <Badge variant="primary" size="sm">
                    Featured
                  </Badge>
                )}
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm font-medium text-primary-600">{skill.version}</div>
            <div className="text-xs text-neutral-500">{skill.author}</div>
          </div>
        </div>

        <p className="text-neutral-600 text-sm line-clamp-2 mb-4">{skill.description}</p>

        <div className="flex items-center justify-between text-sm text-neutral-500">
          <div className="flex items-center gap-2">
            <Star className="w-4 h-4 text-yellow-500" />
            <span>{skill.rating.toFixed(1)}</span>
          </div>
          <div>{skill.downloads.toLocaleString()} downloads</div>
        </div>
      </CardContent>

      <CardFooter className="px-6 py-4 bg-neutral-50 border-t border-neutral-200">
        {skill.isInstalled ? (
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onUninstall(skill);
            }}
            className="w-full"
          >
            Uninstall
          </Button>
        ) : (
          <Button
            variant="primary"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onInstall(skill);
            }}
            className="w-full"
          >
            Install
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
