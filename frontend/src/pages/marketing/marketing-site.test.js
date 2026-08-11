/**
 * @jest-environment node
 */
const fs = require("fs");
const path = require("path");

const read = (rel) => fs.readFileSync(path.join(__dirname, rel), "utf8");
const readJson = (rel) => JSON.parse(read(rel));

describe("Sprint 30 marketing site", () => {
  const app = read("../../App.js");
  const home = read("./HomePage.jsx");
  const pricing = read("./PricingPage.jsx");
  const security = read("./SecurityPage.jsx");
  const en = readJson("../../i18n/locales/marketing-en.json");
  const nl = readJson("../../i18n/locales/marketing-nl.json");

  test("public homepage is wired and product routes exist", () => {
    expect(app).toMatch(/path="\/"\s+element=\{<HomePage/);
    expect(app).toMatch(/\/product\/copilot/);
    expect(app).toMatch(/\/pricing/);
    expect(app).toMatch(/\/faq/);
    expect(app).toMatch(/\/security/);
    expect(app).not.toMatch(/path="\/"\s+element=\{<Navigate to="\/dashboard"/);
  });

  test("hero copy is concrete in both languages", () => {
    expect(en.marketing.hero.headline).toMatch(/Run your business with AI/i);
    expect(nl.marketing.hero.headline).toMatch(/Beheer je bedrijf slimmer met AI/i);
    expect(home).toMatch(/marketing-hero/);
    expect(home).toMatch(/DashboardMock/);
  });

  test("pricing has no checkout when billing is disabled path", () => {
    expect(pricing).toMatch(/BILLING_ENABLED/);
    expect(pricing).not.toMatch(/checkout|stripe|Subscribe now/i);
    expect(pricing).toMatch(/marketing-pricing/);
  });

  test("security page avoids fake certifications", () => {
    const secEn = JSON.stringify(en.marketing.security || {});
    expect(secEn).not.toMatch(/SOC 2|ISO 27001|HIPAA|certified/i);
    expect(security).toMatch(/marketing-security/);
  });

  test("no fake social proof metrics in marketing homepage copy", () => {
    const blob = JSON.stringify(en.marketing.hero) + JSON.stringify(en.marketing.finalCta || {});
    expect(blob).not.toMatch(/\$\d|customers worldwide|5-star|testimonial/i);
  });

  test("marketing locale key parity for core sections", () => {
    for (const key of ["hero", "pillars", "modules", "pricing", "faq", "security", "solutions"]) {
      expect(en.marketing[key]).toBeTruthy();
      expect(nl.marketing[key]).toBeTruthy();
    }
  });
});
