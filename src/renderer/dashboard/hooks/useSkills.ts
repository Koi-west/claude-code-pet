import { useState, useEffect } from 'react';
import { Skill } from '../components/SkillsPanel/SkillCard';
import { cacheManager, CACHE_KEYS, CACHE_DURATION } from '../utils/cache';
import { useToast } from '@renderer/shared/components';

// Mock data for skills
const mockSkills: Skill[] = [
  {
    id: '1',
    name: 'Code Assistant',
    description: 'Advanced code analysis and auto-completion for multiple programming languages.',
    category: 'development',
    version: '2.1.3',
    author: 'Anthropic',
    rating: 4.8,
    downloads: 12450,
    isInstalled: false,
    isFeatured: true,
  },
  {
    id: '2',
    name: 'Productivity Booster',
    description: 'Automate repetitive tasks and boost your workflow efficiency.',
    category: 'productivity',
    version: '1.8.2',
    author: 'Tech Innovations',
    rating: 4.6,
    downloads: 8920,
    isInstalled: true,
    isFeatured: false,
  },
  {
    id: '3',
    name: 'Database Manager',
    description: 'Visual database management and query optimization tool.',
    category: 'automation',
    version: '3.0.1',
    author: 'Data Systems',
    rating: 4.5,
    downloads: 6530,
    isInstalled: false,
    isFeatured: true,
  },
  {
    id: '4',
    name: 'System Monitor',
    description: 'Real-time system monitoring and performance analytics.',
    category: 'utility',
    version: '1.5.0',
    author: 'System Tools',
    rating: 4.3,
    downloads: 4210,
    isInstalled: false,
    isFeatured: false,
  },
  {
    id: '5',
    name: 'AI Translator',
    description: 'Advanced multi-language translation with context awareness.',
    category: 'productivity',
    version: '2.3.4',
    author: 'Language Labs',
    rating: 4.7,
    downloads: 15670,
    isInstalled: true,
    isFeatured: true,
  },
  {
    id: '6',
    name: 'Security Scanner',
    description: 'Comprehensive security scanning and vulnerability detection.',
    category: 'utility',
    version: '1.9.5',
    author: 'Security Pro',
    rating: 4.4,
    downloads: 5890,
    isInstalled: false,
    isFeatured: false,
  },
];

export function useSkills() {
  const { showToast } = useToast();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [showInstallWizard, setShowInstallWizard] = useState(false);
  const [installingSkill, setInstallingSkill] = useState<Skill | null>(null);

  useEffect(() => {
    // Check cache first
    const cachedSkills = cacheManager.get<Skill[]>(CACHE_KEYS.SKILLS, CACHE_DURATION.SKILLS);

    if (cachedSkills) {
      setSkills(cachedSkills);
      setLoading(false);
      return;
    }

    // Simulate API call to fetch skills
    const fetchSkills = async () => {
      try {
        setLoading(true);
        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, 800));

        // Cache the data
        cacheManager.set(CACHE_KEYS.SKILLS, mockSkills, CACHE_DURATION.SKILLS);

        setSkills(mockSkills);
        setError(null);
      } catch (err) {
        setError('Failed to fetch skills');
        console.error('Error fetching skills:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchSkills();
  }, []);

  const handleSkillSelect = (skill: Skill) => {
    setSelectedSkill(skill);
  };

  const clearSelectedSkill = () => {
    setSelectedSkill(null);
  };

  const handleSkillInstall = (skill: Skill) => {
    setInstallingSkill(skill);
    setShowInstallWizard(true);
  };

  const handleSkillUninstall = async (skill: Skill) => {
    try {
      // Simulate uninstall process
      await new Promise(resolve => setTimeout(resolve, 1000));

      setSkills(prev => {
        const updated = prev.map(s =>
          s.id === skill.id ? { ...s, isInstalled: false } : s
        );

        // Update cache
        cacheManager.set(CACHE_KEYS.SKILLS, updated, CACHE_DURATION.SKILLS);

        return updated;
      });

      if (selectedSkill?.id === skill.id) {
        setSelectedSkill(prev => prev ? { ...prev, isInstalled: false } : null);
      }

      showToast({
        type: 'info',
        title: 'Skill removed',
        message: `${skill.name} has been uninstalled.`,
      });
    } catch (err) {
      setError('Failed to uninstall skill');
      console.error('Error uninstalling skill:', err);
      showToast({
        type: 'error',
        title: 'Uninstall failed',
        message: 'Please try again.',
      });
    }
  };

  const handleInstallComplete = async () => {
    if (installingSkill) {
      try {
        setSkills(prev => {
          const updated = prev.map(s =>
            s.id === installingSkill.id ? { ...s, isInstalled: true } : s
          );

          // Update cache
          cacheManager.set(CACHE_KEYS.SKILLS, updated, CACHE_DURATION.SKILLS);

          return updated;
        });

        if (selectedSkill?.id === installingSkill.id) {
          setSelectedSkill(prev => prev ? { ...prev, isInstalled: true } : null);
        }
        showToast({
          type: 'success',
          title: 'Skill installed',
          message: `${installingSkill.name} is ready to use.`,
        });
      } catch (err) {
        setError('Failed to complete installation');
        console.error('Error completing installation:', err);
        showToast({
          type: 'error',
          title: 'Install failed',
          message: 'Please try again.',
        });
      } finally {
        setShowInstallWizard(false);
        setInstallingSkill(null);
      }
    }
  };

  const handleInstallCancel = () => {
    setShowInstallWizard(false);
    setInstallingSkill(null);
  };

  return {
    skills,
    loading,
    error,
    selectedSkill,
    showInstallWizard,
    installingSkill,
    handleSkillSelect,
    clearSelectedSkill,
    handleSkillInstall,
    handleSkillUninstall,
    handleInstallComplete,
    handleInstallCancel,
  };
}
