import GuideSection, { Ui, type GuideFact, type GuideStep } from './GuideSection';
import PhoneFrame, { Choice, Field, Lines, MailCard, NavBar, Notice, Row, ScreenButton, Sheet, TabBar } from './PhoneFrame';

const TABS = ['Chats', 'Contacts', 'Discover', 'Me'];

/*
 * Flow: Me → Services (Pay) → Wallet → Transactions (Bill) → top-right menu
 * → Download Statement → "For personal reconciliation" → dates (up to
 * 3 months) + email + payment password → zip by email within 24 h, unzip
 * password in the WeChat Pay chat. Sources (checked 2026-10): Qianji WeChat
 * import guide, Extrabux statement guide, CSDN export walkthroughs.
 */
const STEPS: GuideStep[] = [
  {
    title: (
      <>
        Tap <Ui>Me</Ui>, then <Ui>Services</Ui>, then <Ui>Wallet</Ui>.
      </>
    ),
    varies: 'Older versions say "Pay" instead of "Services".',
    screen: (
      <PhoneFrame label="WeChat Me tab with the Services row marked">
        <NavBar title="Me" />
        <Row y={52} label="Services" highlight />
        <Row y={76} />
        <Row y={100} />
        <Row y={124} />
        <TabBar items={TABS} active={3} highlight={3} />
      </PhoneFrame>
    ),
  },
  {
    title: (
      <>
        In Wallet, tap <Ui>Transactions</Ui> at the top right.
      </>
    ),
    varies: 'Some versions call it "Bill".',
    screen: (
      <PhoneFrame label="WeChat Wallet page with Transactions marked at the top right">
        <NavBar title="" right="Transactions" rightHighlight back />
        <Row y={52} />
        <Row y={76} />
        <Row y={100} />
        <Row y={124} />
      </PhoneFrame>
    ),
  },
  {
    title: (
      <>
        Tap the menu at the top right and choose <Ui>Download Statement</Ui>.
      </>
    ),
    varies: 'In some versions the menu is "FAQ" or "···"; wait for the list to finish loading first.',
    screen: (
      <PhoneFrame label="Transactions page with the menu open and Download Statement marked">
        <NavBar title="Transactions" right="···" back />
        <Lines y={56} count={6} />
        <Sheet options={['Download Statement', 'Statistics', 'Help']} highlight={0} />
      </PhoneFrame>
    ),
  },
  {
    title: (
      <>
        Choose <Ui>For Personal Reconciliation</Ui>.
      </>
    ),
    body: 'This sends a spreadsheet. The "proof" option sends a PDF, which we cannot read.',
    screen: (
      <PhoneFrame label="Purpose choice with For Personal Reconciliation selected">
        <NavBar title="Download" back />
        <Choice y={54} label="Personal reconciliation" selected highlight />
        <Choice y={78} label="Use as proof (PDF)" />
        <ScreenButton y={176} label="Next" primary />
      </PhoneFrame>
    ),
  },
  {
    title: (
      <>
        Pick the dates, enter your email, and confirm with your payment password.
      </>
    ),
    body: 'Most versions allow up to 3 months per request. For a longer period, repeat it.',
    screen: (
      <PhoneFrame label="Form with a time range, an email field and a Next button">
        <NavBar title="Time range" back />
        <Choice y={52} label="Last month" />
        <Choice y={74} label="Last 3 months" selected />
        <Field y={108} label="Email" value="you@mail.com" />
        <ScreenButton y={176} label="Next" primary />
      </PhoneFrame>
    ),
  },
  {
    title: (
      <>
        Download the <Ui>.zip</Ui> from the email and unzip it with the password from the <Ui>WeChat Pay</Ui> chat.
      </>
    ),
    body: 'Upload the .xlsx (or .csv) file inside, not the .zip.',
    screen: (
      <PhoneFrame label="Email from WeChat Pay with a zip attachment, and a message with the unzip password">
        <NavBar title="Inbox" />
        <MailCard y={52} from="WeChat Pay" subject="Statement file" attachment="statement.zip" />
        <Notice y={124} title="WeChat Pay" body="Unzip password: ••••••" />
      </PhoneFrame>
    ),
  },
];

const FACTS: GuideFact[] = [
  { term: 'You get', detail: 'An email with a password-protected .zip. Inside: an .xlsx file (older exports: .csv).' },
  { term: 'Password', detail: 'Sent as a message in the WeChat Pay chat in WeChat.' },
  { term: 'Typical wait', detail: 'Often under an hour. WeChat allows up to 24 hours.' },
  { term: 'How far back', detail: 'Up to 3 months per request in most versions. Repeat for earlier periods.' },
];

export default function WeChatSteps() {
  return (
    <GuideSection
      id="wechat"
      title="WeChat Pay"
      intro={
        <>
          Six steps inside WeChat, then a file by email. To switch WeChat to English:{' '}
          <span className="text-ink">Me → Settings → General → Language → English</span>.
        </>
      }
      facts={FACTS}
      steps={STEPS}
    />
  );
}
