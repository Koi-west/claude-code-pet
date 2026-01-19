import React from 'react';
import { Card, CardContent, CardFooter } from '@renderer/shared/components';
import { Badge } from '@renderer/shared/components';
import { Button } from '@renderer/shared/components';
import { Skill } from './SkillCard';
import { Code, Zap, Database, ArrowRight, ExternalLink, Shield, Globe, Star, Download } from 'lucide-react';

interface SkillDetailProps {
  skill: Skill;
  onBack: () => void;
  onInstall: () => void;
  onUninstall: () => void;
}

export function SkillDetail({ skill, onBack, onInstall, onUninstall }: SkillDetailProps) {
  const categoryIcons = {
    development: Code,
    productivity: Zap,
    automation: Database,
    utility: ArrowRight,
  };

  const CategoryIcon = categoryIcons[skill.category];

  const features = [
    'Enhanced code analysis',
    'Real-time debugging',
    'Integration with external APIs',
    'Customizable workflows',
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" onClick={onBack}>
          Back
        </Button>
        <h2 className="text-2xl font-bold text-neutral-900">{skill.name}</h2>
        <Badge variant="outline" size="sm">
          v{skill.version}
        </Badge>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Skill Info */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-primary-100 rounded-lg">
                  <CategoryIcon className="w-6 h-6 text-primary-600" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-neutral-900 mb-2">{skill.name}</h3>
                  <p className="text-neutral-600 mb-4">{skill.description}</p>

                  <div className="flex items-center gap-4 mb-4">
                    <div className="flex items-center gap-2 text-sm text-neutral-500">
                      <Star className="w-4 h-4 text-yellow-500" />
                      <span>{skill.rating.toFixed(1)} Rating</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-neutral-500">
                      <Download className="w-4 h-4 text-blue-500" />
                      <span>{skill.downloads.toLocaleString()} Downloads</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-sm text-neutral-500">
                    <div className="flex items-center gap-1">
                      <Shield className="w-4 h-4" />
                      <span>Verified Author</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Globe className="w-4 h-4" />
                      <span>{skill.author}</span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
            <CardFooter className="px-6 py-4 bg-neutral-50 border-t border-neutral-200">
              {skill.isInstalled ? (
                <Button variant="outline" size="base" onClick={onUninstall} className="w-full">
                  Uninstall Skill
                </Button>
              ) : (
                <Button variant="primary" size="base" onClick={onInstall} className="w-full">
                  Install Skill
                </Button>
              )}
            </CardFooter>
          </Card>

          {/* Features */}
          <Card>
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold text-neutral-900 mb-4">Key Features</h3>
              <ul className="space-y-2">
                {features.map((feature, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <div className="mt-1.5 w-1.5 h-1.5 bg-primary-500 rounded-full flex-shrink-0" />
                    <span className="text-neutral-600">{feature}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {/* Documentation */}
          <Card>
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold text-neutral-900 mb-4">Documentation</h3>
              <p className="text-neutral-600 mb-4">
                Comprehensive documentation is available to help you get started with this skill.
              </p>
              <Button variant="outline" size="sm">
                <ExternalLink className="w-4 h-4 mr-2" />
                View Documentation
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Installation Info */}
        <div className="space-y-6">
          <Card>
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold text-neutral-900 mb-4">Installation</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    Status
                  </label>
                  <Badge variant={skill.isInstalled ? 'success' : 'neutral'} size="base">
                    {skill.isInstalled ? 'Installed' : 'Not Installed'}
                  </Badge>
                </div>

                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    Category
                  </label>
                  <Badge variant="outline" size="base">
                    {skill.category}
                  </Badge>
                </div>

                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    Compatibility
                  </label>
                  <div className="flex gap-2">
                    <Badge variant="outline" size="sm">macOS</Badge>
                    <Badge variant="outline" size="sm">Windows</Badge>
                    <Badge variant="outline" size="sm">Linux</Badge>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    Size
                  </label>
                  <div className="text-sm text-neutral-600">~2.5 MB</div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    Last Updated
                  </label>
                  <div className="text-sm text-neutral-600">2 weeks ago</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold text-neutral-900 mb-4">Support</h3>
              <p className="text-neutral-600 text-sm mb-4">
                Need help with this skill? Check our support resources.
              </p>
              <Button variant="outline" size="sm" className="w-full">
                Get Support
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
