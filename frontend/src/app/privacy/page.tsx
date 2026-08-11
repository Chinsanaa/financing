import type { Metadata } from 'next';
import LegalPageLayout, { LegalSection } from '@/components/legal/LegalPageLayout';

export const metadata: Metadata = {
  title: 'Privacy Policy — Financing.',
  description: 'How Financing collects, uses, and protects your data.',
};

const LAST_UPDATED = 'August 11, 2026';

export default function PrivacyPolicyPage() {
  return (
    <LegalPageLayout title="Privacy Policy" lastUpdated={LAST_UPDATED}>
      <p>
        Financing (&ldquo;we&rdquo;, &ldquo;our&rdquo;, &ldquo;the service&rdquo;) helps you
        categorize personal transactions from Alipay and WeChat statements using a machine
        learning model trained on your own labels. This policy explains what data we collect,
        how we use it, and the choices you have.
      </p>

      <LegalSection title="1. Information we collect">
        <ul className="list-disc space-y-1.5 pl-5">
          <li>
            <strong className="text-ink">Account information:</strong> your email address and
            authentication credentials, managed by our authentication provider, Supabase.
          </li>
          <li>
            <strong className="text-ink">Uploaded statements:</strong> the Alipay/WeChat CSV or
            Excel files you upload, stored so they can be re-parsed if needed.
          </li>
          <li>
            <strong className="text-ink">Transaction data:</strong> merchant names,
            descriptions, amounts, and timestamps extracted from your uploaded statements.
          </li>
          <li>
            <strong className="text-ink">Categories and labels:</strong> the categories you
            create and the labels you assign to transactions, used to train your personal
            classification model.
          </li>
          <li>
            <strong className="text-ink">Financial preferences:</strong> optional figures you
            provide, such as monthly income and budget/savings goals.
          </li>
          <li>
            <strong className="text-ink">Model artifacts:</strong> the trained machine learning
            model produced from your labels, stored so it can classify new transactions without
            retraining from scratch every time.
          </li>
        </ul>
        <p>
          We do not use third-party analytics or advertising trackers on this site.
        </p>
      </LegalSection>

      <LegalSection title="2. How we use your information">
        <ul className="list-disc space-y-1.5 pl-5">
          <li>To parse, normalize, and display your transactions on your dashboard.</li>
          <li>
            To train and run a machine learning classifier personal to your account, so future
            transactions can be categorized automatically.
          </li>
          <li>To compute budgets, savings projections, and spending reports for you.</li>
          <li>To authenticate you and keep your account secure.</li>
        </ul>
        <p>We do not sell your data, and we do not use your data to train models for other users.</p>
      </LegalSection>

      <LegalSection title="3. How your data is stored and protected">
        <p>
          Your data is stored in a Postgres database with row-level security, meaning the
          database itself enforces that your records are only ever readable in the context of
          your account. Uploaded files and trained model artifacts are stored in isolated,
          per-user storage buckets. Every request to our backend is authenticated with a signed
          session token before any data is read or written.
        </p>
        <p>
          Our infrastructure is provided by Supabase (authentication, database, and file
          storage), Railway (backend hosting), and Vercel (frontend hosting).
          <span className="text-ink"> [Confirm and list the specific hosting region(s) for these providers before publishing.]</span>
        </p>
      </LegalSection>

      <LegalSection title="4. Data retention and deletion">
        <p>
          You can permanently delete your account at any time from{' '}
          <span className="text-ink">Settings → Danger zone</span>. Doing so removes your
          uploaded files and trained models from storage and deletes your profile,
          transactions, categories, rules, and budget data from our database. This action
          cannot be undone.
        </p>
      </LegalSection>

      <LegalSection title="5. Your choices">
        <ul className="list-disc space-y-1.5 pl-5">
          <li>You can export your transaction history at any time from Settings.</li>
          <li>You can edit or delete individual categories, rules, and transactions.</li>
          <li>You can delete your account and all associated data at any time.</li>
        </ul>
      </LegalSection>

      <LegalSection title="6. Changes to this policy">
        <p>
          We may update this policy as the product changes. We&rsquo;ll update the &ldquo;Last
          updated&rdquo; date above when we do.
        </p>
      </LegalSection>

      <LegalSection title="7. Contact">
        <p>
          Questions about this policy or your data can be sent to{' '}
          <span className="text-ink">[support email address]</span>.
        </p>
      </LegalSection>

      <p className="border-t border-edge/8 pt-6 text-xs">
        This page is a working draft based on how Financing currently handles data. It is not a
        substitute for legal advice — have it reviewed before relying on it as a binding policy.
      </p>
    </LegalPageLayout>
  );
}
