/**
 * @jest-environment node
 */
const fs = require("fs");
const path = require("path");

const read = (rel) => fs.readFileSync(path.join(__dirname, rel), "utf8");
const readJson = (rel) => JSON.parse(read(rel));

describe("Sprint 31 marketing site 2.0", () => {
  const app = read("../../App.js");
  const home = read("./HomePage.jsx");
  const shell = read("../../components/marketing/MarketingShell.jsx");
  const pricing = read("./PricingPage.jsx");
  const security = read("./SecurityPage.jsx");
  const en = readJson("../../i18n/locales/marketing-en.json");
  const nl = readJson("../../i18n/locales/marketing-nl.json");

  test("public homepage is wired and product routes exist", () => {
    expect(app).toMatch(/path="\/"/);
    expect(app).toMatch(/HomePage/);
    expect(app).toMatch(/lazy\(/);
    expect(app).toMatch(/\/product\/copilot/);
    expect(app).toMatch(/\/pricing/);
    expect(app).toMatch(/\/faq/);
    expect(app).toMatch(/\/security/);
  });

  test("light marketing shell and sell-focused hero", () => {
    expect(shell).toMatch(/data-theme="light"/);
    expect(en.marketing.hero.headline).toMatch(/One workspace|AI that thinks/i);
    expect(nl.marketing.hero.headline).toMatch(/Eén werkplek|AI die met je meedenkt/i);
    expect(home).toMatch(/marketing-hero/);
    expect(home).toMatch(/what-is-assistify/);
    expect(home).toMatch(/without-with/);
    expect(home).toMatch(/product-showcase/);
    expect(home).toMatch(/#product-showcase/);
  });

  test("What is Assistify copy is concrete", () => {
    expect(en.marketing.whatIs.p1).toMatch(/clients|projects|proposals/i);
    expect(nl.marketing.whatIs.p1).toMatch(/klanten|projecten|offertes/i);
    expect(en.marketing.whatIs.p2).toMatch(/workspace context|AI/i);
    expect(nl.marketing.whatIs.p2).toMatch(/workspace|AI/i);
  });

  test("pricing has no checkout", () => {
    expect(pricing).toMatch(/BILLING_ENABLED/);
    expect(pricing).not.toMatch(/checkout|stripe|Subscribe now/i);
  });

  test("security page avoids fake certifications", () => {
    const secEn = JSON.stringify(en.marketing.security || {});
    expect(secEn).not.toMatch(/SOC 2|ISO 27001|HIPAA|certified/i);
    expect(security).toMatch(/marketing-security/);
  });

  test("no fake social proof", () => {
    const blob = JSON.stringify(en.marketing.hero) + JSON.stringify(en.marketing.trust || {});
    expect(blob).not.toMatch(/\$\d|customers worldwide|5-star|testimonial/i);
  });

  test("marketing locale key parity for core Sprint 31 sections", () => {
    for (const key of [
      "hero", "whatIs", "withoutWith", "showcase", "aiContext",
      "capabilities", "workflows", "trust", "pricing", "faq", "security",
    ]) {
      expect(en.marketing[key]).toBeTruthy();
      expect(nl.marketing[key]).toBeTruthy();
    }
  });
});
