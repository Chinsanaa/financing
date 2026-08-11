import { Check } from 'lucide-react';
import Badge from '@/components/ui/Badge';

const REQUIREMENTS: { label: string; test: (password: string) => boolean }[] = [
  { label: '9+ chars', test: (p) => p.length >= 9 },
  { label: 'A-Z', test: (p) => /[A-Z]/.test(p) },
  { label: 'a-z', test: (p) => /[a-z]/.test(p) },
  { label: '0-9', test: (p) => /[0-9]/.test(p) },
  { label: '!@#$', test: (p) => /[!@#$%^&*(),.?":{}|<>_\-+=~`[\]\\/;']/.test(p) },
];

export function passwordMeetsRequirements(password: string): boolean {
  return REQUIREMENTS.every(({ test }) => test(password));
}

export default function PasswordChecklist({ password }: { password: string }) {
  return (
    <div className="flex flex-wrap gap-1.5" aria-live="polite">
      {REQUIREMENTS.map(({ label, test }) => {
        const met = test(password);
        return (
          <Badge key={label} tone={met ? 'success' : 'neutral'}>
            {met && <Check className="mr-1 h-3 w-3" aria-hidden="true" />}
            {label}
          </Badge>
        );
      })}
    </div>
  );
}
