import "./styles.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="header">
          <div className="container row">
            <a className="brand" href="/">Mushroom Farm App</a>
            <nav className="nav">
              <a href="/batches">Batches</a>
              <a href="/batches/new">New Batch</a>
            </nav>
          </div>
        </header>
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
