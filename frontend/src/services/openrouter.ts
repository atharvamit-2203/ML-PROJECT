const OPENROUTER_API_KEY = "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";
const SITE_URL = window.location.origin;
const SITE_NAME = "QuantTrade AI";

export async function getStockAnalysis(symbol: string, currentPrice: number, predictedPrice: number, change: number) {
    try {
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
            Keep it professional, data-driven, and under 200 words. Use markdown formatting.`
                    }
                ]
            })
        });

        const data = await response.json();
        return data.choices[0].message.content;
    } catch (error) {
        console.error("OpenRouter Error:", error);
        return "Error generating AI analysis. Please check your API configuration.";
    }
}
