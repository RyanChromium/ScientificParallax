import { ArrowUpRight } from 'lucide-react';
import type { getCopy } from '@/lib/copy';

type PageCopy = ReturnType<typeof getCopy>;
type Example = PageCopy['examples'][number];

function FlowArrow({ x }: { x: number }) {
  return (
    <g className="diagram-flow" aria-hidden="true">
      <path d={`M ${x} 116 H ${x + 38}`} />
      <path d={`M ${x + 31} 109 L ${x + 38} 116 L ${x + 31} 123`} />
    </g>
  );
}

function BrownianDiagram() {
  return (
    <>
      <g transform="translate(8 0)">
        <path
          className="diagram-trace"
          d="M54 174 L72 144 L58 121 L92 98 L78 69 L115 53 L137 80 L171 68"
        />
        <circle className="diagram-object" cx="54" cy="174" r="15" />
        <circle
          className="diagram-object diagram-object-end"
          cx="171"
          cy="68"
          r="15"
        />
        {[44, 79, 112, 145, 181].map((x, i) => (
          <circle
            className="diagram-particle"
            cx={x}
            cy={[55, 184, 135, 164, 122][i]}
            r="3.5"
            key={x}
          />
        ))}
      </g>
      <FlowArrow x={224} />
      <g transform="translate(284 32)">
        <path className="diagram-axis" d="M0 154 V12 M0 154 H150" />
        <path className="diagram-guide" d="M0 126 L150 34" />
        {[18, 43, 70, 98, 126, 148].map((x, i) => (
          <circle
            className="diagram-datum"
            cx={x}
            cy={[116, 105, 86, 79, 53, 39][i]}
            r="5"
            key={x}
          />
        ))}
      </g>
      <FlowArrow x={474} />
      <g transform="translate(546 25)">
        <circle
          className="diagram-object diagram-object-large"
          cx="70"
          cy="84"
          r="28"
        />
        {[
          [15, 32, 45, 61],
          [126, 24, 99, 58],
          [13, 133, 44, 105],
          [132, 137, 101, 108],
          [69, 6, 69, 45],
          [72, 164, 72, 125],
        ].map(([x1, y1, x2, y2]) => (
          <g className="diagram-collision" key={`${x1}-${y1}`}>
            <circle cx={x1} cy={y1} r="4" />
            <path d={`M${x1} ${y1} L${x2} ${y2}`} />
          </g>
        ))}
      </g>
    </>
  );
}

function GravityDiagram() {
  return (
    <>
      <g transform="translate(18 16)">
        <circle className="diagram-planet" cx="82" cy="112" r="46" />
        <circle className="diagram-object" cx="152" cy="35" r="13" />
        <path className="diagram-force" d="M145 51 Q126 75 106 91" />
        <path className="diagram-force-tip" d="M108 80 L106 91 L117 89" />
      </g>
      <FlowArrow x={224} />
      <g transform="translate(282 12)">
        <path
          className="diagram-grid"
          d="M0 45 Q76 94 154 45 M0 78 Q76 128 154 78 M0 111 Q76 161 154 111 M0 144 Q76 194 154 144"
        />
        <path
          className="diagram-grid"
          d="M18 25 Q47 104 18 176 M58 25 Q70 104 58 176 M98 25 Q86 104 98 176 M138 25 Q108 104 138 176"
        />
        <circle className="diagram-planet" cx="77" cy="109" r="27" />
      </g>
      <FlowArrow x={474} />
      <g transform="translate(534 18)">
        <circle className="diagram-planet" cx="76" cy="103" r="34" />
        <path
          className="diagram-light"
          d="M0 40 Q68 42 106 75 Q136 101 171 92"
        />
        <path className="diagram-ray" d="M2 40 H25" />
        <path className="diagram-ray" d="M151 96 L171 92" />
      </g>
    </>
  );
}

function TinyArrow({
  x,
  y,
  angle = 0,
}: {
  x: number;
  y: number;
  angle?: number;
}) {
  return (
    <g
      className="diagram-spin"
      transform={`translate(${x} ${y}) rotate(${angle})`}
    >
      <path d="M-13 0 H13" />
      <path d="M7 -6 L13 0 L7 6" />
    </g>
  );
}

function SymmetryDiagram() {
  const positions = [
    [28, 42, -30],
    [78, 40, 65],
    [128, 43, 155],
    [43, 91, 115],
    [103, 92, -78],
    [153, 91, 22],
    [28, 141, 205],
    [78, 140, -12],
    [133, 141, 82],
  ] as const;
  return (
    <>
      <g transform="translate(20 28)">
        {positions.map(([x, y, angle]) => (
          <TinyArrow x={x} y={y} angle={angle} key={`${x}-${y}`} />
        ))}
      </g>
      <FlowArrow x={224} />
      <g transform="translate(292 28)">
        {positions.map(([x, y]) => (
          <TinyArrow x={x} y={y} key={`${x}-${y}`} />
        ))}
      </g>
      <FlowArrow x={474} />
      <g transform="translate(544 22)">
        <path
          className="diagram-field"
          d="M4 44 H156 M4 77 H156 M4 110 H156 M4 143 H156"
        />
        <circle className="diagram-vacuum" cx="80" cy="94" r="48" />
        <path
          className="diagram-wave"
          d="M22 94 C38 67 50 121 67 94 S97 67 113 94 S140 121 154 94"
        />
        <circle
          className="diagram-object diagram-object-small"
          cx="80"
          cy="94"
          r="12"
        />
      </g>
    </>
  );
}

function CaseDiagram({ example }: { example: Example }) {
  return (
    <figure className={`case-figure case-figure-${example.kind}`}>
      <svg
        className="case-diagram"
        viewBox="0 0 720 220"
        role="img"
        aria-labelledby={`diagram-${example.kind}`}
        data-example-diagram={example.kind}
      >
        <title id={`diagram-${example.kind}`}>{example.diagramAlt}</title>
        {example.kind === 'brownian' && <BrownianDiagram />}
        {example.kind === 'gravity' && <GravityDiagram />}
        {example.kind === 'symmetry' && <SymmetryDiagram />}
      </svg>
      <figcaption className="diagram-stages">
        {example.diagram.map((stage) => (
          <span key={stage}>{stage}</span>
        ))}
      </figcaption>
    </figure>
  );
}

export default function PerspectiveExamples({ copy }: { copy: PageCopy }) {
  return (
    <section className="examples-section page-width" id="examples">
      <div className="examples-heading">
        <p className="section-label">{copy.examplesLabel}</p>
        <div>
          <h2>
            {copy.examplesTitle[0]}
            <br />
            <span>{copy.examplesTitle[1]}</span>
          </h2>
          <p>{copy.examplesIntro}</p>
        </div>
      </div>
      <div className="case-studies">
        {copy.examples.map((example) => (
          <article className="case-study" key={example.kind}>
            <div className="case-copy">
              <p className="case-field">{example.field}</p>
              <h3>{example.title}</h3>
              <p>{example.body}</p>
              <a href={example.sourceHref} target="_blank" rel="noreferrer">
                {copy.exampleSource} <ArrowUpRight size={14} />
              </a>
            </div>
            <CaseDiagram example={example} />
          </article>
        ))}
      </div>
    </section>
  );
}
