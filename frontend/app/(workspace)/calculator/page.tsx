"use client";
import { useMutation } from "@tanstack/react-query";
import { Calculator, Check, ArrowRight } from "lucide-react";
import { api, money, TaxResult } from "@/lib/api";
import { ErrorMessage, PageTitle } from "@/components/ui";
export default function TaxCalculator() {
  const comparison = useMutation({
    mutationFn: (data: FormData) =>
      api<TaxResult>("/tax/compare", {
        method: "POST",
        body: JSON.stringify({
          annual_salary: Number(data.get("salary")),
          old_regime_deductions: Number(data.get("deductions")),
        }),
      }),
  });
  return (
    <>
      <PageTitle eyebrow="AY 2026–27 · FY 2025–26" title="Know your options.">
        Compare your estimated tax under the old and new regimes.
      </PageTitle>
      <div className="calculator-grid">
        <section className="panel">
          <div className="panel-heading">
            <h2>Start with your numbers</h2>
            <Calculator size={23} />
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              comparison.mutate(new FormData(e.currentTarget));
            }}
          >
            <label>
              Annual gross salary (₹)
              <input
                name="salary"
                type="number"
                required
                min="0"
                max="5000000"
                step="0.01"
                defaultValue="1200000"
              />
              <small>Before standard deduction. Up to ₹50,00,000.</small>
            </label>
            <label>
              Old-regime deductions (₹)
              <input
                name="deductions"
                type="number"
                required
                min="0"
                max="2000000"
                step="0.01"
                defaultValue="150000"
              />
              <small>
                Eligible deductions excluding standard deduction, which is
                applied automatically.
              </small>
            </label>
            <ErrorMessage error={comparison.error} />
            <button className="button full" disabled={comparison.isPending}>
              {comparison.isPending ? "Comparing…" : "Compare regimes"}
              <ArrowRight size={18} />
            </button>
          </form>
        </section>
        <div className="calculator-context">
          <p className="eyebrow">A HELPFUL STARTING POINT</p>
          <h2>
            See the numbers.
            <br />
            Consider the whole picture.
          </h2>
          <p>
            This estimator covers resident salaried individuals under 60, with
            salary income up to ₹50 lakh.
          </p>
          <ul>
            <li>Standard deductions applied automatically</li>
            <li>Eligible rebates and cess included</li>
            <li>Capital gains and special-rate income excluded</li>
          </ul>
          <p className="quiet">
            Use the correct assessment year. This calculator does not cover
            later assessment years.
          </p>
        </div>
      </div>
      {comparison.data && (
        <section className="comparison" aria-live="polite">
          <div className="saving-banner">
            <span className="check-icon">
              <Check size={22} />
            </span>
            <div>
              <h2>
                {Number(comparison.data.estimated_saving) === 0
                  ? "Both estimates are equal."
                  : `The ${comparison.data.recommended_regime.toLowerCase()} regime has the lower estimate.`}
              </h2>
              <p>
                Estimated difference:{" "}
                <strong>{money(comparison.data.estimated_saving)}</strong> ·{" "}
                {comparison.data.assessment_year}
              </p>
            </div>
          </div>
          <div className="regime-grid">
            {(["old", "new"] as const).map((regime) => {
              const data = comparison.data![`${regime}_regime`];
              const recommended =
                comparison.data!.recommended_regime === regime.toUpperCase();
              return (
                <article
                  className={`panel regime-card ${recommended ? "recommended" : ""}`}
                  key={regime}
                >
                  <div className="panel-heading">
                    <h3>{regime === "old" ? "Old" : "New"} regime</h3>
                    {recommended && (
                      <span className="tag">Lower or equal estimate</span>
                    )}
                  </div>
                  <p className="tax-total">{money(data.total_tax)}</p>
                  <p className="quiet">Estimated annual tax</p>
                  <dl>
                    <div>
                      <dt>Taxable income</dt>
                      <dd>{money(data.taxable_income)}</dd>
                    </div>
                    <div>
                      <dt>Tax before cess</dt>
                      <dd>{money(data.tax_before_cess)}</dd>
                    </div>
                    <div>
                      <dt>Health & education cess</dt>
                      <dd>{money(data.cess)}</dd>
                    </div>
                  </dl>
                </article>
              );
            })}
          </div>
          <p className="notice">{comparison.data.disclaimer}</p>
        </section>
      )}
    </>
  );
}
