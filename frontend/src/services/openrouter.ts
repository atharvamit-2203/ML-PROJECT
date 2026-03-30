const OPENROUTER_API_KEY = (import.meta as any).env?.VITE_OPENROUTER_API_KEY || "";
const SITE_URL = window.location.origin;
const SITE_NAME = "QuantTrade AI";

function buildLocalAnalysis(symbol: string, currentPrice: number, predictedPrice: number, change: number) {
    const outlook = change > 1 ? "Bullish" : change < -1 ? "Bearish" : "Neutral";
    const absMove = Math.abs(change).toFixed(2);
    const momentum = change >= 0 ? "upside momentum" : "downside pressure";

    return `### Technical Outlook: ${outlook}

- **Current Price:** Rs ${currentPrice.toFixed(2)}
- **Forecast Price:** Rs ${predictedPrice.toFixed(2)}
- **Expected Move:** ${change.toFixed(2)}%

**Risk Factors**
- Elevated short-term volatility can invalidate directional signals.
- Macro news/events may drive gaps beyond model assumptions.
- Liquidity changes can amplify intraday swings.

**Sentiment Summary**
Model points to **${momentum}** with an estimated move of **${absMove}%** over the selected horizon. Treat this as decision support, not financial advice.

### ML Concepts Used In This App
- **Regression:** Linear Regression and Gradient Boosting Regressor for future price forecasting.
- **Classification:** Random Forest (UP/DOWN direction) and Multinomial Logistic Regression (SELL/NEUTRAL/STRONG_BUY).
- **Feature Engineering:** Lag-based features from recent prices/returns.
- **Time-Series Framing:** Autoregressive next-step prediction using rolling historical windows.`;
}

export async function getStockAnalysis(symbol: string, currentPrice: number, predictedPrice: number, change: number) {
    try {
        if (!OPENROUTER_API_KEY) {
            return buildLocalAnalysis(symbol, currentPrice, predictedPrice, change);
        }

        const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${OPENROUTER_API_KEY}`,
                "HTTP-Referer": SITE_URL,
                "X-Title": SITE_NAME,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                "model": "google/gemini-2.0-flash-001",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional financial analyst AI. Provide concise, high-impact stock market analysis."
                    },
                    {
                        "role": "user",
                        "content": `Analyze the stock ${symbol}. Current Price: ₹${currentPrice.toFixed(2)}. 14-day Predicted Price: ₹${predictedPrice.toFixed(2)} (${change.toFixed(2)}% change). 
            Provide:
            1. Technical Outlook (Bullish/Bearish/Neutral)
            2. Key Risk Factors for this specific stock
            3. Sentiment Analysis summary
            4. ML Concepts Used in this app, clearly mentioning:
               - Regression (Linear Regression and Gradient Boosting Regressor)
               - Classification (Random Forest and Multinomial Logistic Regression)
               - Lag-based features and time-series forecasting setup
            Keep it professional, data-driven, and under 220 words. Use markdown formatting with short bullet points.`
                    }
                ]
            })
        });

        if (!response.ok) {
            return buildLocalAnalysis(symbol, currentPrice, predictedPrice, change);
        }

        const data = await response.json();
        return data?.choices?.[0]?.message?.content || buildLocalAnalysis(symbol, currentPrice, predictedPrice, change);
    } catch (error) {
        console.error("OpenRouter Error:", error);
        return buildLocalAnalysis(symbol, currentPrice, predictedPrice, change);
    }
}
