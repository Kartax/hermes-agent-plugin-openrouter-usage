(function () {
  "use strict";

  const SDK = window.__HERMES_PLUGIN_SDK__;
  const { React } = SDK;
  const { useState, useEffect, useCallback } = SDK.hooks;
  const {
    Card, CardHeader, CardTitle, CardContent,
  } = SDK.components;
  const { fetchJSON } = SDK;

  function fmtCredits(n) {
    if (n >= 1e6) return "$" + (n / 1e6).toFixed(2) + "M";
    if (n >= 1e3) return "$" + (n / 1e3).toFixed(2) + "K";
    return "$" + Number(n).toFixed(2);
  }

  function fmtTokens(n) {
    if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
    if (n >= 1e3) return (n / 1e3).toFixed(0) + "K";
    return String(n);
  }

  function fmtNum(n) {
    return Number(n).toLocaleString();
  }

  function OpenRouterUsagePage() {
    const [usage, setUsage] = useState(null);
    const [activity, setActivity] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const loadData = useCallback(async function () {
      setLoading(true);
      setError(null);
      try {
        var u = await fetchJSON("/api/plugins/openrouter-usage/usage?period=24h");
        setUsage(u);
        var a = await fetchJSON("/api/plugins/openrouter-usage/activity?period=7d").catch(function () { return null; });
        setActivity(a);
      } catch (err) {
        setError(err.message || "Failed to load data");
      } finally {
        setLoading(false);
      }
    }, []);

    useEffect(function () { loadData(); }, [loadData]);

    if (loading && !usage) {
      return React.createElement("div", { className: "pt-0 pb-6 px-6" },
        React.createElement("div", { className: "text-muted-foreground text-sm" }, "Loading..."),
      );
    }

    if (error) {
      return React.createElement("div", { className: "pt-0 pb-6 px-6" },
        React.createElement(Card, null,
          React.createElement(CardContent, { className: "p-4 text-destructive" }, "Error: " + error),
        ),
      );
    }

    if (!usage || usage.error) {
      return React.createElement("div", { className: "pt-0 pb-6 px-6" },
        React.createElement(Card, null,
          React.createElement(CardContent, { className: "p-4 text-destructive" },
            "Error: " + (usage ? usage.error : "No data"),
          ),
        ),
      );
    }

    var hasMgmtKey = activity && !activity.error;

    return React.createElement("div", { className: "pt-0 pb-6 flex flex-col gap-6" },

      // ── One-liner: Available + Today (full-width card) ──
      React.createElement(Card, { className: "mb-6" },
        React.createElement(CardContent, { className: "p-4" },
          React.createElement("div", { className: "flex justify-between items-baseline text-sm" },
            React.createElement("span", null,
              React.createElement("span", { className: "text-muted-foreground" }, "Spent today: "),
              React.createElement("span", { className: "font-medium" }, fmtCredits(usage.usage_daily)),
            ),
            React.createElement("span", null,
              React.createElement("span", { className: "text-muted-foreground" }, "Available Credits: "),
              React.createElement("span", { className: "font-semibold text-primary" }, "$" + usage.remaining.toFixed(2)),
            ),
          ),
        ),
      ),

      // ── Recent Activity (nur mit Management Key) ──
      hasMgmtKey
        ? React.createElement("div", { className: "flex flex-col gap-6" },

            activity.top_models && activity.top_models.length > 0
              ? React.createElement(Card, { className: "mb-6" },
                  React.createElement(CardHeader, { className: "pb-2" },
                    React.createElement(CardTitle, null, "Top Models (last 7 days)"),
                  ),
                  React.createElement(CardContent, null,
                    React.createElement("div", { className: "space-y-1" },
                      activity.top_models.map(function (m, i) {
                        return React.createElement("div", {
                          key: m.model,
                          className: "flex justify-between py-1.5 border-b border-border/40 last:border-0",
                        },
                          React.createElement("span", { className: "text-sm" },
                            (i + 1) + ". " + (m.model.split("/").pop() || m.model)
                          ),
                          React.createElement("span", { className: "text-sm text-muted-foreground" },
                            fmtNum(m.requests) + " req / " + fmtTokens(m.tokens) + " / " + fmtCredits(m.cost)
                          ),
                        );
                      }),
                    ),
                  ),
                )
              : null,

            activity.recent_entries && activity.recent_entries.length > 0
              ? React.createElement(Card, { className: "mb-6" },
                  React.createElement(CardHeader, { className: "pb-2" },
                    React.createElement(CardTitle, null, "Recent Activity (last 7 days)"),
                  ),
                  React.createElement(CardContent, null,
                    React.createElement("div", { className: "overflow-x-auto" },
                      React.createElement("table", { className: "w-full text-xs" },
                        React.createElement("thead", null,
                          React.createElement("tr", { className: "border-b border-border/40 text-muted-foreground" },
                            React.createElement("th", { className: "text-left py-1 pr-2 whitespace-nowrap" }, "Date"),
                            React.createElement("th", { className: "text-left py-1 px-2" }, "Model"),
                            React.createElement("th", { className: "text-right py-1 px-2" }, "Req"),
                            React.createElement("th", { className: "text-right py-1 px-2" }, "Tokens"),
                            React.createElement("th", { className: "text-right py-1 pl-2" }, "Cost"),
                          ),
                        ),
                        React.createElement("tbody", null,
                          activity.recent_entries.map(function (e, i) {
                            return React.createElement("tr", {
                              key: i,
                              className: "border-b border-border/20 hover:bg-muted/30",
                            },
                              React.createElement("td", { className: "py-1 pr-2 text-muted-foreground whitespace-nowrap" }, e.date || "\u2014"),
                              React.createElement("td", { className: "py-1 px-2 font-mono" },
                                (e.model || "").split("/").pop() || "?"
                              ),
                              React.createElement("td", { className: "text-right py-1 px-2" }, fmtNum(e.requests || 0)),
                              React.createElement("td", { className: "text-right py-1 px-2" }, fmtTokens(e.total_tokens || 0)),
                              React.createElement("td", { className: "text-right py-1 pl-2" }, fmtCredits(e.cost || 0)),
                            );
                          }),
                        ),
                      ),
                    ),
                  ),
                )
              : null,
          )

        : React.createElement(Card, { className: "mb-6" },
            React.createElement(CardContent, { className: "p-6 text-center" },
              React.createElement("p", { className: "text-sm text-muted-foreground mb-2" },
                "Request/token-level activity requires an OpenRouter Management Key."
              ),
              React.createElement("p", { className: "text-xs text-muted-foreground" },
                "Create one at openrouter.ai/keys and set OPENROUTER_MANAGEMENT_API_KEY in your .env file.",
              ),
            ),
          ),
    );
  }

  window.__HERMES_PLUGINS__.register("openrouter-usage", OpenRouterUsagePage);
})();