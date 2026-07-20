// frontend/src/components/login/NeonGridBackground.tsx
export default function NeonGridBackground() {
  return (
    <div className="neon-grid pointer-events-none" aria-hidden="true" data-testid="login-background">
      <div className="neon-grid__ambient" />
      <div className="neon-grid__floor" />
      <div className="neon-grid__glow" />
      <div className="neon-grid__vignette" />
    </div>
  );
}
