import type { Metadata } from 'next';
import LegalPageLayout, { LegalSection } from '@/components/legal/LegalPageLayout';

export const metadata: Metadata = {
  title: 'Terms & Conditions — Financing.',
  description: 'The terms that govern your use of Financing.',
};

const LAST_UPDATED = 'August 11, 2026';

export default function TermsPage() {
  return (
    <LegalPageLayout title="Terms & Conditions" lastUpdated={LAST_UPDATED}>
      <p>
        These terms govern your use of Financing (&ldquo;the service&rdquo;). By creating an
        account, you agree to them.
      </p>

      <LegalSection title="1. Your account">
        <p>
          You must provide accurate information when creating an account and are responsible
          for keeping your login credentials secure. You&rsquo;re responsible for all activity
          that happens under your account.
        </p>
      </LegalSection>

      <LegalSection title="2. Acceptable use">
        <ul className="list-disc space-y-1.5 pl-5">
          <li>
            Only upload financial statements that belong to you or that you have explicit
            authorization to upload and process.
          </li>
          <li>Do not attempt to access another user&rsquo;s account or data.</li>
          <li>
            Do not use the service to upload malicious files or attempt to disrupt or reverse
            engineer the platform.
          </li>
        </ul>
      </LegalSection>

      <LegalSection title="3. Not financial advice">
        <p>
          Financing categorizes transactions using a machine learning model trained on labels
          you provide. Categorizations, budgets, and savings projections are provided for
          informational purposes only and may contain errors — they are not financial, tax, or
          investment advice. Always verify figures independently before making financial
          decisions.
        </p>
      </LegalSection>

      <LegalSection title="4. Your data and content">
        <p>
          You retain ownership of the statements and data you upload. You grant us permission
          to process that data solely to provide the service to you, as described in our{' '}
          <span className="text-ink">Privacy Policy</span>. You can export or delete your data
          at any time from Settings.
        </p>
      </LegalSection>

      <LegalSection title="5. Service availability">
        <p>
          The service is provided &ldquo;as is&rdquo;, without warranty of any kind. We do not
          guarantee the service will be uninterrupted, error-free, or that categorization
          accuracy will meet any particular standard. We may modify or discontinue features at
          any time.
        </p>
      </LegalSection>

      <LegalSection title="6. Limitation of liability">
        <p>
          To the maximum extent permitted by law, Financing and its operators are not liable
          for any indirect, incidental, or consequential damages arising from your use of the
          service, including financial decisions made based on categorized data or reports.
        </p>
      </LegalSection>

      <LegalSection title="7. Account termination">
        <p>
          You may delete your account at any time from Settings. We may suspend or terminate
          accounts that violate these terms.
        </p>
      </LegalSection>

      <LegalSection title="8. Governing law">
        <p>
          These terms are governed by the laws of{' '}
          <span className="text-ink">[jurisdiction to be confirmed]</span>, without regard to
          conflict-of-law principles.
        </p>
      </LegalSection>

      <LegalSection title="9. Changes to these terms">
        <p>
          We may update these terms as the product evolves. We&rsquo;ll update the &ldquo;Last
          updated&rdquo; date above when we do. Continued use of the service after changes means
          you accept the updated terms.
        </p>
      </LegalSection>

      <LegalSection title="10. Contact">
        <p>
          Questions about these terms can be sent to{' '}
          <span className="text-ink">[support email address]</span>.
        </p>
      </LegalSection>

      <p className="border-t border-edge/8 pt-6 text-xs">
        This page is a working draft based on how Financing currently works. It is not a
        substitute for legal advice — have it reviewed before relying on it as a binding
        agreement.
      </p>
    </LegalPageLayout>
  );
}
