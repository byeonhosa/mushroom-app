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
              <a href="/blocks">Blocks</a>
              <a href="/blocks/new">New Block</a>
              <a href="/inoculations/new">New Inoculation</a>
              <a href="/harvest/new">New Harvest</a>
              <a href="/spawn-batches">Spawn Batches</a>
              <a href="/sterilization-runs">Sterilization Runs</a>
              <a href="/grain-types">Grain Types</a>
              <a href="/ingredients">Ingredients</a>
              <a href="/pasteurization-runs">Pasteurization Runs</a>
            </nav>
          </div>
        </header>
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
