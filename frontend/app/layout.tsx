import "./styles.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="header">
          <div className="container row">
            <a className="brand" href="/">Mushroom Farm App</a>
            <nav className="nav">
              <a href="/bags">Bags</a>
              <a href="/bags/create/spawn">Create Spawn Records</a>
              <a href="/events/spawn-inoculation">Spawn Inoculation</a>
              <a href="/bags/create/substrate">Create Substrate Records</a>
              <a href="/events/incubation">Incubation Start</a>
              <a href="/events/ready">Ready</a>
              <a href="/events/inoculation">Substrate Inoculation</a>
              <a href="/events/fruiting">Fruiting Start</a>
              <a href="/events/harvest">Harvest</a>
              <a href="/events/disposal">Disposal</a>
              <a href="/reports">Reports</a>
              <a href="/species">Species</a>
              <a href="/liquid-cultures">Liquid Cultures</a>
              <a href="/pasteurization-runs">Pasteurization</a>
              <a href="/sterilization-runs">Sterilization</a>
              <a href="/mix-lots">Mix Lots</a>
            </nav>
          </div>
        </header>
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
