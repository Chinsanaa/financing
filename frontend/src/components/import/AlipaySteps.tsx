import GuideSection, { Ui, type GuideFact, type GuideStep } from './GuideSection';
import PhoneFrame, { Choice, Field, Lines, MailCard, NavBar, Notice, Row, ScreenButton, Sheet, TabBar } from './PhoneFrame';

const TABS = ['Home', 'Wealth', 'Messages', 'Me'];

/*
 * Flow: Me → Bills → "···" → transaction statement → "For personal
 * reconciliation" → dates + email → zip by email, password separately.
 * Sources (checked 2026-10): Qianji import guide, Extrabux statement guide,
 * Zhihu export guides — see the D3 report. English labels differ between
 * app versions, so each step says what else it may be called.
 */
const STEPS: GuideStep[] = [
  {
    title: (
      <>
        Open Alipay, tap <Ui>Me</Ui> at the bottom right, then <Ui>Bills</Ui>.
      </>
    ),
    varies: 'Some versions say "Bill" or "Transactions".',
    screen: (
      <PhoneFrame label="Alipay Me tab with the Bills row marked">
        <NavBar title="Me" />
        <Row y={52} />
        <Row y={76} label="Bills" highlight />
        <Row y={100} />
        <Row y={124} />
        <Row y={148} />
        <TabBar items={TABS} active={3} highlight={3} />
      </PhoneFrame>
    ),
  },
  {
    title: (
      <>
        Tap <Ui>···</Ui> at the top right, then the option to issue a <Ui>transaction statement</Ui>.
      </>
    ),
    varies: 'The menu item may read "Transaction records" or "Statement certificate".',
    screen: (
      <PhoneFrame label="Alipay Bills page with the menu open and Transaction statement marked">
        <NavBar title="Bills" right="···" back />
        <Lines y={56} count={6} />
        <Sheet options={['Transaction statement', 'Bill settings', 'Help']} highlight={0} />
      </PhoneFrame>
    ),
  },
  {
    title: (
      <>
        Choose <Ui>For personal reconciliation</Ui>.
      </>
    ),
    body: 'This one sends a spreadsheet (CSV). The "proof" option sends a PDF, which we cannot read.',
    screen: (
      <PhoneFrame label="Purpose choice with For personal reconciliation selected">
        <NavBar title="Purpose" back />
        <Choice y={54} label="For personal reconciliation" selected highlight />
        <Choice y={78} label="Proof (PDF)" />
        <ScreenButton y={176} label="Next" primary />
      </PhoneFrame>
    ),
  },
  {
    title: (
      <>
        Pick the dates, enter your email, and confirm with your payment password or face check.
      </>
    ),
    body: 'One request covers up to 12 months. For older months, make another request.',
    screen: (
      <PhoneFrame label="Form with start date, end date and email fields">
        <NavBar title="Statement" back />
        <Field y={58} label="From" value="2026-01-01" />
        <Field y={84} label="To" value="2026-09-30" />
        <Field y={110} label="Email" value="you@mail.com" />
        <ScreenButton y={176} label="Send" primary />
      </PhoneFrame>
    ),
  },
  {
    title: (
      <>
        Download the <Ui>.zip</Ui> from the email and unzip it with the password Alipay gives you.
      </>
    ),
    body: 'Upload the .csv file inside, not the .zip.',
    varies:
      'The password arrives in your Alipay messages or by SMS. In some versions it is the last six digits of your ID or passport number.',
    screen: (
      <PhoneFrame label="Email from Alipay with a zip attachment, and a message with the unzip password">
        <NavBar title="Inbox" />
        <MailCard y={52} from="Alipay" subject="Your transaction statement" attachment="statement.zip" />
        <Notice y={124} title="Unzip password" body="Shown in Alipay / SMS" />
      </PhoneFrame>
    ),
  },
];

const FACTS: GuideFact[] = [
  { term: 'You get', detail: 'An email with a password-protected .zip. Inside: one .csv file.' },
  { term: 'Password', detail: 'Sent separately, in your Alipay messages or by SMS.' },
  { term: 'Typical wait', detail: 'Usually a few minutes. It can take a few hours.' },
  { term: 'How far back', detail: 'Up to 12 months per request. Repeat for earlier periods.' },
];

export default function AlipaySteps() {
  return (
    <GuideSection
      id="alipay"
      title="Alipay"
      intro={
        <>
          Five steps on your phone, then a file arrives by email. If your Alipay is in Chinese, switch it first:{' '}
          <span className="text-ink">Me → Settings → General → Language → English</span> (labels may vary by version).
        </>
      }
      facts={FACTS}
      steps={STEPS}
    />
  );
}
