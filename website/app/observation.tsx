'use client';
import { useState } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { ringPaths, views, type View } from '@/lib/projection';
import type { chinese } from '@/lib/copy';

export default function Observation({
  copy,
}: {
  copy: typeof chinese.observation;
}) {
  const [view, setView] = useState<View>('oblique');
  return (
    <Tabs
      value={view}
      onValueChange={(value) => setView(value as View)}
      className="observation"
    >
      <div className="instrument-label">
        <span>{copy.heading}</span>
        <span>θ {Math.round((views[view].angle * 180) / Math.PI)}°</span>
      </div>
      <div className="optical-field">
        <svg
          viewBox="0 0 520 470"
          role="img"
          aria-labelledby="projection-title projection-description"
          className="projection"
        >
          <title id="projection-title">{`${copy.titlePrefix}${copy.views[view].label}${copy.titleSuffix}`}</title>
          <desc id="projection-description">{copy.description}</desc>
          <circle cx="260" cy="235" r="219" className="field-boundary" />
          <path d="M24 235H496 M260 12V458" className="field-axis" />
          <g className="projected-object" key={view}>
            {ringPaths(view).map((ring) => (
              <path
                key={ring.id}
                d={ring.d}
                fill="none"
                stroke={ring.depth > 0 ? 'var(--cobalt)' : 'var(--cyan)'}
                strokeWidth={ring.depth > 0 ? 1.15 : 0.8}
                opacity={ring.depth > 0 ? 0.86 : 0.43}
              />
            ))}
          </g>
          <circle cx="260" cy="235" r="2.3" fill="var(--cobalt)" />
          <text x="479" y="254" className="axis-caption">
            x′
          </text>
          <text x="270" y="27" className="axis-caption">
            y′
          </text>
        </svg>
        <span className="object-note">
          {copy.object}
          <br />
          <strong>{copy.ways}</strong>
        </span>
      </div>
      <div className="observation-controls">
        <span>{copy.switch}</span>
        <TabsList className="projection-tabs" aria-label={copy.label}>
          {(Object.keys(views) as View[]).map((key) => (
            <TabsTrigger key={key} value={key} className="projection-tab">
              {copy.views[key].label}
            </TabsTrigger>
          ))}
        </TabsList>
      </div>
      {(Object.keys(views) as View[]).map((key) => (
        <TabsContent key={key} value={key} className="projection-description">
          <p>{copy.views[key].description}</p>
        </TabsContent>
      ))}
      <p className="concept-disclaimer">{copy.disclaimer}</p>
    </Tabs>
  );
}
