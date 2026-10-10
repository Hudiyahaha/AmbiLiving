"use client";

import Image from "next/image";
import Link from "next/link";

function LogoMark() {
  return (
    <span className="logo-mark" aria-hidden>
      <span />
    </span>
  );
}

export function LandingPage() {
  return (
    <div className="landing">
      <header className="site-header">
        <div className="wrap">
          <a href="#top" className="logo">
            <LogoMark />
            AmbiLiving
          </a>
          <nav className="nav-links" aria-label="Primary">
            <a href="#why">Why it matters</a>
            <a href="#how-it-works">How it works</a>
            <a href="#product">The product</a>
            <a href="#research">Research</a>
          </nav>
          <Link href="/dashboard" className="btn btn-primary">
            Open dashboard
          </Link>
        </div>
      </header>

      <main id="top">
        <section className="hero" aria-label="AmbiLiving">
          <Image
            src="/landing/hero-wide.jpg"
            alt="Elderly woman reading in a warm sunlit living room"
            fill
            priority
            className="hero-image"
            sizes="100vw"
          />
          <div className="hero-scrim" aria-hidden />
          <h1 className="hero-brand">AmbiLiving</h1>
        </section>

        <section className="intro" id="intro">
          <div className="wrap intro-layout">
            <div className="intro-copy">
              <p className="intro-kicker">Ambient activity monitoring</p>
              <h2>
                Know how they&apos;re really doing — without watching them do
                it.
              </h2>
              <p className="lede">
                AmbiLiving reads motion, doors, and temperature already in the
                home, then turns those signals into plain-language daily
                activity — so family can tell an ordinary Tuesday from a day
                that needs attention.
              </p>
              <div className="intro-actions">
                <Link href="/monitoring" className="btn btn-primary">
                  See monitoring
                </Link>
                <a href="#how-it-works" className="btn btn-ghost-on-light">
                  How it works
                </a>
              </div>
              <ul className="intro-points">
                <li>No cameras in the home</li>
                <li>Nothing to wear or charge</li>
                <li>Built for caregivers, not engineers</li>
              </ul>
            </div>
            <aside className="intro-aside" aria-label="What you see">
              <p className="aside-label">Today at a glance</p>
              <div className="aside-row">
                <span className="aside-time">07:10</span>
                <span>Morning routine</span>
              </div>
              <div className="aside-row">
                <span className="aside-time">08:05</span>
                <span>Meal preparation</span>
              </div>
              <div className="aside-row is-active">
                <span className="aside-time">09:54</span>
                <span>Relaxing · living room</span>
              </div>
              <div className="aside-row">
                <span className="aside-time">13:30</span>
                <span>Leave home</span>
              </div>
              <p className="aside-note">
                Activities, not sensor codes — the same language you already
                use when you call to check in.
              </p>
            </aside>
          </div>
        </section>

        <section className="pain" id="why">
          <div className="wrap">
            <div className="section-head">
              <h2>What families try — and what still falls short</h2>
              <p className="lede">
                Most households already piece together a patchwork of help. Each
                piece covers part of the worry; none of them quietly cover the
                whole day.
              </p>
            </div>
            <div className="pain-grid">
              <article className="pain-card">
                <span className="pain-num">01</span>
                <h3>Paid help can&apos;t cover every hour</h3>
                <p>
                  There are 168 hours in a week. An aide covers only some of
                  them. AmbiLiving stays with the home the rest of the time —
                  quietly, around the clock.
                </p>
              </article>
              <article className="pain-card">
                <span className="pain-num">02</span>
                <h3>Pendants get left behind</h3>
                <p>
                  A pendant only helps if it&apos;s worn and pressed in the
                  moment. Ambient sensors don&apos;t ask anyone to remember
                  anything.
                </p>
              </article>
              <article className="pain-card">
                <span className="pain-num">03</span>
                <h3>A check-in is only a moment</h3>
                <p>
                  A call captures one point in time. AmbiLiving notices patterns
                  across the day — missed meals, long stillness, unusual nights.
                </p>
              </article>
              <article className="pain-card">
                <span className="pain-num">04</span>
                <h3>&ldquo;I&apos;m fine&rdquo; isn&apos;t always enough</h3>
                <p>
                  Self-assessment can slip before anyone names it. Discreet
                  monitoring respects dignity without relying only on what they
                  say.
                </p>
              </article>
            </div>
          </div>
        </section>

        <section className="pipeline" id="how-it-works">
          <div className="wrap">
            <div className="section-head">
              <h2>From a motion sensor to a moment of reassurance</h2>
              <p className="lede">
                Every alert AmbiLiving sends travels the same short path — from
                a raw physical event to something worth telling a caregiver.
              </p>
            </div>
            <ol className="pipeline-flow">
              <li className="pipe-step">
                <span className="pipe-num">1</span>
                <h3>Ambient sensing</h3>
                <p>
                  Motion, door, and temperature sensors blend into walls and
                  doorframes — nothing to wear, charge, or point at anyone.
                </p>
              </li>
              <li className="pipe-step">
                <span className="pipe-num">2</span>
                <h3>Activity recognition</h3>
                <p>
                  Patterns become activities: meal preparation, sleep, bathing,
                  leaving home — not a stream of ON/OFF codes.
                </p>
              </li>
              <li className="pipe-step">
                <span className="pipe-num">3</span>
                <h3>Routine comparison</h3>
                <p>
                  Each day is checked against that person&apos;s own habits —
                  not a generic average across every household.
                </p>
              </li>
              <li className="pipe-step">
                <span className="pipe-num">4</span>
                <h3>Caregiver insight</h3>
                <p>
                  You hear when something is genuinely different — not every
                  time a light switches on somewhere in the house.
                </p>
              </li>
            </ol>
          </div>
        </section>

        <section className="approach" id="approach">
          <div className="wrap">
            <div className="section-head">
              <h2>Sensors you&apos;ll forget are even there</h2>
              <p className="lede">
                Three ways to sense daily life in a home — and why ambient
                sensors are the only option that stays out of the way.
              </p>
            </div>
            <div className="approach-grid">
              <article className="approach-card">
                <div className="approach-icon" aria-hidden>
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <rect x="7" y="7" width="10" height="12" rx="2" />
                    <path d="M9 4h6v3H9zM9 17h6v3H9z" />
                  </svg>
                </div>
                <h3>Wearables</h3>
                <p>
                  Only work when remembered, worn, and charged. Missed exactly
                  when they matter most — a shower, a nightstand, a forgotten
                  charge.
                </p>
              </article>
              <article className="approach-card">
                <div className="approach-icon" aria-hidden>
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <rect x="2" y="6" width="15" height="12" rx="2" />
                    <path d="M17 10l5-3v10l-5-3" />
                  </svg>
                </div>
                <h3>Cameras</h3>
                <p>
                  Capture private moments people don&apos;t want recorded —
                  bedrooms, bathrooms, getting dressed.
                </p>
              </article>
              <article className="approach-card is-chosen">
                <div className="approach-icon" aria-hidden>
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M12 20h.01" />
                    <path d="M8.5 16.5a5 5 0 0 1 7 0" />
                    <path d="M5 13a10 10 0 0 1 14 0" />
                  </svg>
                </div>
                <h3>Ambient sensors</h3>
                <p>
                  No footage. Nothing to wear. Ordinary sensors read a routine
                  without recording an image.
                </p>
                <span className="approach-tag">AmbiLiving&apos;s approach</span>
              </article>
            </div>
          </div>
        </section>

        <section className="product" id="product">
          <div className="wrap">
            <div className="section-head">
              <h2>One dashboard, the whole day at a glance</h2>
              <p className="lede">
                Monitoring, history, and alerts built around activities — the
                same views a family would actually open.
              </p>
            </div>
            <div className="feature-grid">
              <Link href="/monitoring" className="feature-card">
                <div className="feature-visual" aria-hidden>
                  <svg viewBox="0 0 220 130" width="82%">
                    <rect
                      x="4"
                      y="4"
                      width="98"
                      height="122"
                      rx="3"
                      fill="#F2F5F1"
                      stroke="#DCE3DE"
                    />
                    <rect
                      x="106"
                      y="4"
                      width="110"
                      height="60"
                      rx="3"
                      fill="#F4F0E8"
                      stroke="#DCE3DE"
                    />
                    <rect
                      x="106"
                      y="68"
                      width="110"
                      height="58"
                      rx="3"
                      fill="#E7EEF2"
                      stroke="#DCE3DE"
                    />
                    <circle cx="40" cy="40" r="4" fill="#2F6F5E" />
                    <circle cx="70" cy="90" r="4" fill="#2F6F5E" />
                    <circle cx="160" cy="30" r="4" fill="#2F6F5E" />
                    <circle cx="150" cy="100" r="4" fill="#3A6D9B" />
                  </svg>
                </div>
                <h3>Live floor plan</h3>
                <p>
                  Watch activity move through the home room by room — without a
                  single video frame.
                </p>
              </Link>
              <Link href="/activities" className="feature-card">
                <div className="feature-visual" aria-hidden>
                  <div className="mini-timeline">
                    <div className="mini-row">
                      <span className="mini-label">07:10</span>
                      <div
                        className="mini-bar"
                        style={{ width: "34%", background: "#ABC6BD" }}
                      />
                    </div>
                    <div className="mini-row">
                      <span className="mini-label">08:05</span>
                      <div
                        className="mini-bar"
                        style={{ width: "58%", background: "#3F6B52" }}
                      />
                    </div>
                    <div className="mini-row">
                      <span className="mini-label">09:54</span>
                      <div
                        className="mini-bar"
                        style={{ width: "22%", background: "#C17A2F" }}
                      />
                    </div>
                    <div className="mini-row">
                      <span className="mini-label">13:30</span>
                      <div
                        className="mini-bar"
                        style={{ width: "70%", background: "#ABC6BD" }}
                      />
                    </div>
                  </div>
                </div>
                <h3>Activity history</h3>
                <p>
                  Scroll the day as a readable timeline of activities — not a
                  spreadsheet of sensor codes.
                </p>
              </Link>
              <Link href="/anomalies" className="feature-card">
                <div className="feature-visual" aria-hidden>
                  <div className="mini-alert">
                    <div className="mini-alert-top">
                      <span className="mini-alert-dot" />
                      <span>Unusual stillness</span>
                    </div>
                    <p>
                      No motion in living areas since 2:40 AM — longer than her
                      typical pattern.
                    </p>
                  </div>
                </div>
                <h3>Anomaly alerts</h3>
                <p>
                  A nudge only when a routine breaks — a missed meal, long
                  stillness, or a 3am wander.
                </p>
              </Link>
            </div>
          </div>
        </section>

        <section className="research" id="research">
          <div className="wrap">
            <div className="section-head">
              <h2>Grounded in real ambient-sensor research</h2>
              <p className="lede research-lede">
                Models are developed against CASAS — the Aruba and Milan
                smart-home datasets used across published activity-recognition
                work.
              </p>
            </div>
            <div className="stat-grid">
              <div className="stat-cell">
                <div className="stat-num">6,477</div>
                <p className="stat-label">
                  Labelled activity instances in the Aruba dataset behind the
                  models
                </p>
              </div>
              <div className="stat-cell">
                <div className="stat-num">11+</div>
                <p className="stat-label">
                  Distinct daily activities — from meal prep to sleep to leaving
                  home
                </p>
              </div>
              <div className="stat-cell">
                <div className="stat-num">24/7</div>
                <p className="stat-label">
                  Passive sensing that never stops listening, and never records
                  an image
                </p>
              </div>
            </div>
            <p className="research-note">
              Across published deep-learning approaches on these same datasets,
              reported accuracy has ranged from roughly 90–96%. AmbiLiving&apos;s
              models are built and benchmarked against that same body of
              research.
            </p>
          </div>
        </section>

        <section className="final-cta" id="cta">
          <div className="wrap">
            <h2>
              Give them their independence back. Give yourself peace of mind.
            </h2>
            <p className="lede">
              Explore Aruba and Milan homes with monitoring, history, and
              alerts.
            </p>
            <div className="cta-actions">
              <Link href="/dashboard" className="btn btn-primary">
                Open dashboard
              </Link>
              <a href="#how-it-works" className="btn btn-ghost-on-light">
                How it works
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="wrap footer-row">
          <div className="footer-brand">
            <a href="#top" className="logo">
              <LogoMark />
              AmbiLiving
            </a>
            <p>
              Ambient assisted living — no cameras, no wearables.
            </p>
          </div>
          <p className="footer-copy">© 2026</p>
        </div>
      </footer>
    </div>
  );
}
