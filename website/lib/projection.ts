export type View = 'oblique' | 'front' | 'side';
export const views: Record<
  View,
  { angle: number; label: string; description: string }
> = {
  oblique: {
    angle: 0.86,
    label: '斜视',
    description: '改变观察的角度，环面的层次关系显现。',
  },
  front: {
    angle: 0,
    label: '正面',
    description: '从正面看，同一个环面呈现为同心轮廓。',
  },
  side: {
    angle: Math.PI / 2,
    label: '侧面',
    description: '从侧面看，投影压缩了深度，原本的孔洞不再可见。',
  },
};

// Fixed mathematical torus. Projection changes; the sample set does not.
export function project(u: number, v: number, angle: number) {
  const radius = 138 + 55 * Math.cos(v);
  const x = radius * Math.cos(u);
  const y = radius * Math.sin(u);
  const z = 55 * Math.sin(v);
  const tiltY = y * Math.cos(angle) - z * Math.sin(angle);
  const depth = y * Math.sin(angle) + z * Math.cos(angle);
  const spin = -0.25;
  return {
    x: 260 + x * Math.cos(spin) - tiltY * Math.sin(spin),
    y: 235 + x * Math.sin(spin) + tiltY * Math.cos(spin),
    depth,
  };
}

export function ringPaths(view: View) {
  const angle = views[view].angle;
  return Array.from({ length: 44 }, (_, ring) => {
    const samples = Array.from({ length: 65 }, (_, i) => {
      const phase = (i / 64) * Math.PI * 2;
      return ring < 32
        ? project((ring / 32) * Math.PI * 2, phase, angle)
        : project(phase, ((ring - 32) / 12) * Math.PI * 2, angle);
    });
    return {
      id: ring,
      depth: samples.reduce((n, p) => n + p.depth, 0) / samples.length,
      d:
        samples
          .map(
            (p, i) =>
              `${i === 0 ? 'M' : 'L'}${p.x.toFixed(2)},${p.y.toFixed(2)}`,
          )
          .join(' ') + ' Z',
    };
  }).sort((a, b) => a.depth - b.depth);
}
