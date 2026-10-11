import GuideSection, { Ui, type GuideFact, type GuideStep } from './GuideSection';
import PhoneFrame, { Field, Lines, NavBar, Row, ScreenButton, Sheet } from './PhoneFrame';

/*
 * Banks differ, so these steps are generic. What the importer looks for is
 * the contract in docs/contracts/API_V5.md §3.9: a date column AND an amount
 * column (or debit/credit columns, or an amount + direction column). Card
 * payments to Alipay / Tenpay / WeChat Pay become own-account transfers.
 */
const STEPS: GuideStep[] = [
  {
    title: (
      <>
        Sign in to your bank and open the card&apos;s <Ui>transaction details</Ui>.
      </>
    ),
    body: 'Online banking on a computer usually has more export options than the phone app.',
    varies: 'Banks name this "Transaction history", "Account details" or "Statement".',
    screen: (
      <PhoneFrame label="Bank account page with Transaction details marked">
        <NavBar title="My accounts" />
        <Row y={52} />
        <Row y={76} label="Transaction details" highlight />
        <Row y={100} />
        <Row y={124} />
      </PhoneFrame>
    ),
  },
  {
    title: (
      <>
        Pick the dates and choose <Ui>Export</Ui> or <Ui>Download</Ui> as <Ui>CSV</Ui> or <Ui>Excel (.xlsx)</Ui>.
      </>
    ),
    body: 'Only got an old .xls file? Open it in Excel, Numbers or Google Sheets and save it as .csv. A PDF statement cannot be imported.',
    screen: (
      <PhoneFrame label="Export menu with CSV marked">
        <NavBar title="" right="Export" rightHighlight back />
        <Field y={52} label="Period" value="2026-09-01 – 09-30" />
        <Lines y={82} count={4} />
        <Sheet title="Export as" options={['CSV', 'Excel (.xlsx)', 'PDF']} highlight={0} />
      </PhoneFrame>
    ),
  },
  {
    title: <>Upload the file as it is. We find the columns for you.</>,
    body: 'No renaming or cleaning needed. If the columns cannot be found, the upload says so and nothing is imported.',
    screen: (
      <PhoneFrame label="A downloaded statement.csv file ready to upload">
        <NavBar title="Downloads" />
        <Row y={52} label="statement.csv" highlight chevron={false} />
        <Row y={76} chevron={false} />
        <ScreenButton y={176} label="Upload" primary />
      </PhoneFrame>
    ),
  },
];

const FACTS: GuideFact[] = [
  { term: 'You get', detail: 'A .csv or .xlsx file, usually straight away. No password.' },
  { term: 'How far back', detail: 'Set by your bank; often one to several years.' },
  { term: 'Money in', detail: 'Salary and interest are imported as income.' },
  { term: 'Transfers', detail: 'Moves between your own accounts are imported as transfers, never as spending.' },
];

const SAMPLE: { date: string; text: string; debit: string; credit: string; as: string }[] = [
  { date: '2026-09-10', text: 'Payroll, Acme Shanghai Ltd.', debit: '', credit: '18,000.00', as: 'Income' },
  { date: '2026-09-12', text: 'Alipay top-up', debit: '2,000.00', credit: '', as: 'Transfer' },
  { date: '2026-09-14', text: 'Tenpay (WeChat Pay)', debit: '86.50', credit: '', as: 'Transfer' },
  { date: '2026-09-20', text: 'Card payment, supermarket', debit: '212.60', credit: '', as: 'Spending' },
];

function ColumnGuide() {
  return (
    <div className="mt-12">
      <h3 className="font-display text-xl font-normal">What we look for in the file</h3>
      <p className="mt-2 max-w-[60ch] text-sm leading-relaxed text-muted">
        A <span className="text-ink">date</span> column, plus one of these three ways of writing the amount. English and
        Chinese headers are both recognised.
      </p>
      <ul className="mt-4 divide-y divide-edge/12 border-y border-edge/12 text-sm">
        <li className="grid gap-1 py-3 sm:grid-cols-[12rem,1fr] sm:gap-4">
          <span className="text-ink">One amount column</span>
          <span className="text-muted">Money out and money in in the same column, told apart by the sign.</span>
        </li>
        <li className="grid gap-1 py-3 sm:grid-cols-[12rem,1fr] sm:gap-4">
          <span className="text-ink">Debit and credit columns</span>
          <span className="text-muted">Separate columns, also called withdrawal and deposit.</span>
        </li>
        <li className="grid gap-1 py-3 sm:grid-cols-[12rem,1fr] sm:gap-4">
          <span className="text-ink">Amount + direction</span>
          <span className="text-muted">An amount, and a column saying which way it went (for example Dr/Cr or In/Out).</span>
        </li>
      </ul>

      <div className="mt-8 overflow-x-auto">
        <table className="w-full min-w-[30rem] text-sm">
          <caption className="mb-2 text-left text-[13px] text-muted">
            Example: a debit/credit export, and how each row is imported
          </caption>
          <thead className="border-b border-edge/25 text-left text-[13px] text-muted">
            <tr>
              <th scope="col" className="py-2 pr-3 font-medium">Date</th>
              <th scope="col" className="py-2 pr-3 font-medium">Description</th>
              <th scope="col" className="py-2 pr-3 text-right font-medium">Debit</th>
              <th scope="col" className="py-2 pr-3 text-right font-medium">Credit</th>
              <th scope="col" className="py-2 font-medium">Imported as</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-edge/10">
            {SAMPLE.map((r) => (
              <tr key={r.text}>
                <td className="whitespace-nowrap py-2.5 pr-3 text-muted">{r.date}</td>
                <td className="py-2.5 pr-3">{r.text}</td>
                <td className="num py-2.5 pr-3 text-right">{r.debit}</td>
                <td className="num py-2.5 pr-3 text-right text-positive">{r.credit}</td>
                <td className="py-2.5 font-medium">{r.as}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-4 max-w-[64ch] text-sm leading-relaxed text-muted">
        <span className="text-ink">Nothing is counted twice.</span> When your card pays Alipay or WeChat Pay (Tenpay),
        the bank row is imported as a transfer between your own accounts. The purchase itself is counted once, from
        your Alipay or WeChat statement, where the real merchant is named.
      </p>
    </div>
  );
}

export default function BankCsvSteps() {
  return (
    <GuideSection
      id="bank"
      title="Bank CSV"
      intro={
        <>
          For your salary card or any bank account. Spending, income and transfers on the statement are all imported,
          each kept in its own place.
        </>
      }
      facts={FACTS}
      steps={STEPS}
      aside={<ColumnGuide />}
    />
  );
}
