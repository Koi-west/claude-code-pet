import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@renderer/shared/components';
import { Button } from '@renderer/shared/components';
import { Progress } from '@renderer/shared/components';
import { Skill } from './SkillCard';
import { CheckCircle, Download, Settings, Code, ExternalLink } from 'lucide-react';

interface InstallWizardProps {
  isOpen: boolean;
  skill: Skill | null;
  onClose: () => void;
  onInstallComplete: () => void;
}

export function InstallWizard({ isOpen, skill, onClose, onInstallComplete }: InstallWizardProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [isInstalling, setIsInstalling] = useState(false);
  const [installationProgress, setInstallationProgress] = useState(0);

  const steps = [
    { id: 1, name: 'Review', icon: CheckCircle },
    { id: 2, name: 'Download', icon: Download },
    { id: 3, name: 'Install', icon: Settings },
    { id: 4, name: 'Configure', icon: Code },
    { id: 5, name: 'Complete', icon: CheckCircle },
  ];

  const handleStartInstall = () => {
    setCurrentStep(2);
    setIsInstalling(true);
    setInstallationProgress(0);

    // Simulate installation process
    const interval = setInterval(() => {
      setInstallationProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsInstalling(false);
          setCurrentStep(5);
          return 100;
        }
        return prev + 10;
      });
    }, 300);
  };

  const handleContinue = () => {
    if (currentStep < steps.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleComplete = () => {
    onInstallComplete();
    onClose();
    setCurrentStep(1);
    setInstallationProgress(0);
    setIsInstalling(false);
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-neutral-900">
              Review Installation Details
            </h3>
            <p className="text-neutral-600">
              You are about to install <strong>{skill?.name}</strong> v{skill?.version}.
            </p>
            <div className="bg-neutral-50 rounded-lg p-4">
              <h4 className="font-medium text-neutral-900 mb-2">What will be installed:</h4>
              <ul className="space-y-1 text-sm text-neutral-600">
                <li>• Main application files</li>
                <li>• Configuration settings</li>
                <li>• Dependency packages</li>
                <li>• Documentation and examples</li>
              </ul>
            </div>
          </div>
        );

      case 2:
      case 3:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-neutral-900">
              {currentStep === 2 ? 'Downloading Files' : 'Installing'}
            </h3>
            <div className="bg-neutral-50 rounded-lg p-4">
              <Progress value={installationProgress} className="mb-4" />
              <div className="text-center">
                <div className="text-sm text-neutral-500 mb-2">
                  {isInstalling ? 'Downloading and installing...' : 'Download complete'}
                </div>
                {!isInstalling && currentStep === 3 && (
                  <div className="text-sm text-neutral-500">
                    Configuration files created
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      case 4:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-neutral-900">Configure Skill</h3>
            <p className="text-neutral-600">
              Configure <strong>{skill?.name}</strong> to suit your needs.
            </p>
            <div className="bg-neutral-50 rounded-lg p-4 space-y-3">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Enable Auto Updates
                </label>
                <input type="checkbox" defaultChecked className="rounded border-neutral-300" />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Default Configuration
                </label>
                <select className="w-full px-3 py-2 border border-neutral-300 rounded-lg">
                  <option>Standard</option>
                  <option>Advanced</option>
                  <option>Minimal</option>
                </select>
              </div>
            </div>
          </div>
        );

      case 5:
        return (
          <div className="space-y-4 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold text-neutral-900">
              Installation Complete!
            </h3>
            <p className="text-neutral-600">
              <strong>{skill?.name}</strong> v{skill?.version} has been successfully installed.
            </p>
            <div className="bg-neutral-50 rounded-lg p-4">
              <p className="text-sm text-neutral-600 mb-2">
                What's next?
              </p>
              <ul className="text-left text-sm text-neutral-600 space-y-1">
                <li>• Restart the application if prompted</li>
                <li>• Configure advanced settings in the Skills panel</li>
                <li>• Check documentation for usage examples</li>
              </ul>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <Dialog open={isOpen} onClose={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Install Skill</DialogTitle>
        </DialogHeader>

        {/* Step Indicator */}
        <div className="mb-6">
          <div className="flex justify-between items-center">
            {steps.map((step) => (
              <div
                key={step.id}
                className="flex flex-col items-center flex-1"
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium mb-1 ${
                    step.id < currentStep
                      ? 'bg-green-500 text-white'
                      : step.id === currentStep
                      ? 'bg-primary-500 text-white'
                      : 'bg-neutral-200 text-neutral-500'
                  }`}
                >
                  {step.id < currentStep ? (
                    <CheckCircle className="w-4 h-4" />
                  ) : (
                    step.id
                  )}
                </div>
                <div
                  className={`text-xs font-medium ${
                    step.id < currentStep
                      ? 'text-green-500'
                      : step.id === currentStep
                      ? 'text-primary-500'
                      : 'text-neutral-500'
                  }`}
                >
                  {step.name}
                </div>
              </div>
            ))}
          </div>
          <div className="h-1 bg-neutral-200 rounded-full mt-2">
            <div
              className="h-full bg-primary-500 rounded-full transition-all duration-300"
              style={{ width: `${((currentStep - 1) / (steps.length - 1)) * 100}%` }}
            />
          </div>
        </div>

        {/* Step Content */}
        <div className="mb-6">
          {renderStepContent()}
        </div>

        <DialogFooter>
          {currentStep === 1 && (
            <>
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleStartInstall}>
                Install
              </Button>
            </>
          )}

          {currentStep > 1 && currentStep < 5 && (
            <>
              <Button
                variant="outline"
                onClick={onClose}
                disabled={isInstalling}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleContinue}
                disabled={isInstalling && (currentStep === 2 || currentStep === 3)}
              >
                {isInstalling ? 'Installing...' : 'Continue'}
              </Button>
            </>
          )}

          {currentStep === 5 && (
            <Button variant="primary" onClick={handleComplete}>
              Finish
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}