import { useEffect, useRef } from 'react';

export function useStickToBottom<T extends HTMLElement>(deps: unknown[] = []) {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) {
      return;
    }

    const distanceFromBottom = element.scrollHeight - element.scrollTop - element.clientHeight;
    const shouldStick = distanceFromBottom < 80;

    if (shouldStick) {
      element.scrollTo({
        top: element.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, deps);

  return ref;
}
