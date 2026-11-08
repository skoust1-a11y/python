function Inline({ text }: { text: string }) {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).filter(Boolean);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("`") && part.endsWith("`")) return <code key={i}>{part.slice(1, -1)}</code>;
        if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

function cells(line: string) {
  return line
    .trim()
    .replace(/^\||\|$/g, "")
    .split("|")
    .map((c) => c.trim());
}

function Table({ block }: { block: string }) {
  const lines = block
    .trim()
    .split("\n")
    .filter((line) => line.includes("|") && !/^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+$/.test(line));
  if (lines.length < 2) return <p><Inline text={block} /></p>;
  const head = cells(lines[0]);
  const rows = lines.slice(1).map(cells);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {head.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((c, j) => (
                <td key={j}>{c}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Block({ text }: { text: string }) {
  const trimmed = text.trim();
  if (!trimmed) return null;
  if (/^\*\*[^*]+\*\*$/.test(trimmed)) return <h3>{trimmed.slice(2, -2)}</h3>;
  const lines = trimmed.split("\n");
  if (lines.length >= 2 && lines.every((line) => line.includes("|"))) return <Table block={trimmed} />;
  const out: JSX.Element[] = [];
  let items: string[] = [];
  const flush = () => {
    if (items.length) out.push(<ul key={out.length}>{items.map((t, i) => <li key={i}><Inline text={t} /></li>)}</ul>);
    items = [];
  };
  for (const line of lines) {
    const bullet = line.match(/^\s*(?:[-*]|\d+\.)\s+(.*)/);
    if (bullet) {
      items.push(bullet[1]);
      continue;
    }
    flush();
    const heading = line.match(/^\s*#{1,6}\s+(.*)/);
    if (heading) out.push(<h3 key={out.length}><Inline text={heading[1]} /></h3>);
    else if (/^-{3,}$/.test(line.trim())) out.push(<hr key={out.length} />);
    else if (line.trim()) out.push(<p key={out.length}><Inline text={line.trim().replace(/^\*(?!\*)|(?<!\*)\*$/g, "")} /></p>);
  }
  flush();
  return <>{out}</>;
}

export function AnswerBody({ text }: { text: string }) {
  return (
    <div className="answer">
      {text.split(/\n{2,}/).map((block, i) => (
        <Block key={i} text={block} />
      ))}
    </div>
  );
}
