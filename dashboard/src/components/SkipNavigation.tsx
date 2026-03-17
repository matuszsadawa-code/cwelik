/**
 * SkipNavigation Component
 * 
 * Provides skip navigation links for keyboard users to quickly jump to main content areas.
 * Links are visually hidden but become visible when focused via keyboard.
 * 
 * Validates: Requirements 30.2, 30.10
 */

export default function SkipNavigation() {
  const skipLinks = [
    { id: 'main-content', label: 'Skip to main content' },
    { id: 'navigation', label: 'Skip to navigation' },
    { id: 'header', label: 'Skip to header' },
  ];

  const handleSkipClick = (e: React.MouseEvent<HTMLAnchorElement>, targetId: string) => {
    e.preventDefault();
    const target = document.getElementById(targetId);
    if (target) {
      target.focus();
      // Only call scrollIntoView if it exists (not in test environment)
      if (typeof target.scrollIntoView === 'function') {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  };

  return (
    <nav
      aria-label="Skip navigation"
      className="skip-navigation"
    >
      {skipLinks.map((link) => (
        <a
          key={link.id}
          href={`#${link.id}`}
          onClick={(e) => handleSkipClick(e, link.id)}
          className="skip-link"
        >
          {link.label}
        </a>
      ))}
    </nav>
  );
}
