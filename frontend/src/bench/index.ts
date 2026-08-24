export function bench(_fn: () => void): number {
  const t0 = performance.now();
  _fn();
  return performance.now() - t0;
}
export default bench;
