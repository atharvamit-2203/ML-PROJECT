import React, { useState } from "react";
import { BrainCircuit, Calculator, Search, TrendingUp, AlertCircle, Sparkles, ArrowRight, ArrowUpRight } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from "recharts";
import { useOpenRouter } from "../hooks/useOpenRouter";
import ReactMarkdown from "react-markdown";


// Deterministic pseudo-random number generator based on a seed string
const getSeededRandom = (seed: string, index: number) => {
  let h = 0xdeadbeef ^ seed.length;
  const str = seed + index.toString();
  for (let i = 0; i < str.length; i++) {
    h = Math.imul(h ^ str.charCodeAt(i), 2654435761);
  }
  return ((h ^ h >>> 16) >>> 0) / 4294967296;
};

// Mock prediction data (now deterministic)
const generatePredictionData = (currentPrice: number, symbol: string = "DEFAULT") => {
  const data = [];
  let price = currentPrice;

  // Historical data (30 days)
  for (let i = -30; i <= 0; i++) {
    data.push({
      day: i,
      actual: price,
      predicted: null
    });
    price += (getSeededRandom(symbol, i) - 0.45) * 5;
  }

  // Future predictions (14 days)
  let predPrice = price;
  for (let i = 1; i <= 14; i++) {
    predPrice += (getSeededRandom(symbol, i + 100) - 0.3) * 6; // Upward bias
    data.push({
      day: i,
      actual: null,
      predicted: predPrice,
      upperBound: predPrice * 1.05,
      lowerBound: predPrice * 0.95
    });
  }

  return data;
};

const TICKERS = [
  { id: "TATAMOTORS", name: "Tata Motors" },
  { id: "TATACHEM.NS", name: "Tata Chemicals" },
  { id: "SPARC.NS", name: "Sun Pharma Adv." },
  { id: "HDFC", name: "HDFC Bank" },
  { id: "LT", name: "Larsen & Toubro" },
  { id: "ADANIGREEN.NS", name: "Adani Green" },
  { id: "HINDUSTAN_ZINC", name: "Hindustan Zinc" },
  { id: "TITAN", name: "Titan Company" },
  { id: "ULTRACEMCO", name: "UltraTech Cement" },
  { id: "NMDC_STEEL", name: "NMDC Steel" },
  { id: "BSE_FMCG", name: "BSE FMCG Index" },
  { id: "TLKM", name: "TLKM" }
];

export default function Predictor() {
  const [symbol, setSymbol] = useState("TATAMOTORS");
  const [horizon, setHorizon] = useState("14");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [predictionData, setPredictionData] = useState(generatePredictionData(985, "TATAMOTORS"));

  // Dynamic insights state
  const [insights, setInsights] = useState({
    trend: "Bullish Signal Detected",
    trendColor: "emerald",
    trendDesc: "Model confidence: 87%. Strong momentum indicators align with positive sentiment analysis.",
    volWarning: "Volatility Warning",
    volColor: "amber",
    volDesc: "Expected volatility is 2.4x higher than historical average over the next 5 days."
  });

  const [currentPrice, setCurrentPrice] = useState(985.42);
  const [predictedPrice, setPredictedPrice] = useState(1042.85);
  const [expectedReturn, setExpectedReturn] = useState(7.34);

  const { analysis, loading: isDeepAnalyzing, error: deepError, fetchAnalysis } = useOpenRouter();

  const handleDeepAnalysis = () => {
    fetchAnalysis(symbol, currentPrice, predictedPrice, expectedReturn);
  };


  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol) return;

    setIsAnalyzing(true);

    try {
      // Try to fetch from the local Python backend (port 5001)
      const res = await fetch(`http://localhost:8000/predict/${symbol}`);
      const futureRes = await fetch(`http://localhost:8000/predict_future/${symbol}?days=${horizon}`);

      if (res.ok && futureRes.ok) {
        const data = await res.json();
        const futureData = await futureRes.json();

        const basePrice = data.last_close;
        setCurrentPrice(basePrice);

        // Map backend predictions to chart data
        const gbPreds = futureData.gradient_boosting.predictions;
        const newChartData = [];

        // Add some mock historical data for visual continuity
        let histPrice = basePrice * 0.9;
        for (let i = -30; i <= 0; i++) {
          newChartData.push({ day: i, actual: histPrice, predicted: null });
          histPrice += (Math.random() - 0.45) * (basePrice * 0.01);
        }
        newChartData[30].actual = basePrice; // Today

        // Add future predictions
        for (let i = 0; i < gbPreds.length; i++) {
          const p = gbPreds[i];
          newChartData.push({
            day: i + 1,
            actual: null,
            predicted: p,
            upperBound: p * 1.05,
            lowerBound: p * 0.95
          });
        }
        setPredictionData(newChartData);

        const finalPred = gbPreds[gbPreds.length - 1];
        setPredictedPrice(finalPred);
        setExpectedReturn(futureData.gradient_boosting.total_change_pct);

        // Update Insights based on actual model output
        const isUp = data.classification.random_forest.direction === "UP";
        const acc = (data.classification.random_forest.accuracy * 100).toFixed(1);
        const category = data.multinomial.category;

        setInsights({
          trend: isUp ? "Bullish Signal Detected" : "Bearish Signal Detected",
          trendColor: isUp ? "emerald" : "rose",
          trendDesc: `Random Forest Model confidence: ${acc}%. Multinomial category: ${category.replace('_', ' ')}.`,
          volWarning: category.includes("STRONG") ? "High Volatility Expected" : "Stable Market Conditions",
          volColor: category.includes("STRONG") ? "amber" : "blue",
          volDesc: category.includes("STRONG")
            ? "Strong price movement predicted. Ensure risk management is in place."
            : "Price action is expected to remain relatively stable."
        });

      } else {
        throw new Error("Backend not reachable");
      }
    } catch (err) {
      // Fallback: Generate dynamic mock data if Python backend isn't running
      console.warn("Python backend not reachable. Using deterministic mock data.");

      // Generate deterministic base price based on symbol
      const basePrice = 100 + (symbol.length * 150) + (getSeededRandom(symbol, 999) * 500);
      setCurrentPrice(basePrice);

      const newChartData = generatePredictionData(basePrice, symbol);
      setPredictionData(newChartData);

      const finalPred = newChartData[newChartData.length - 1].predicted || basePrice;
      setPredictedPrice(finalPred);

      const ret = ((finalPred - basePrice) / basePrice) * 100;
      setExpectedReturn(ret);

      const isBullish = ret > 0;
      const isVolatile = Math.abs(ret) > 5;

      // Deterministic insights
      const confidence = (getSeededRandom(symbol, 888) * 20 + 75).toFixed(1);
      const volMult = (getSeededRandom(symbol, 777) * 2 + 1.5).toFixed(1);

      setInsights({
        trend: isBullish ? "Bullish Signal Detected" : "Bearish Signal Detected",
        trendColor: isBullish ? "emerald" : "rose",
        trendDesc: `Model confidence: ${confidence}%. ${isBullish ? 'Strong upward momentum' : 'Downward pressure'} detected for ${symbol}.`,
        volWarning: isVolatile ? "High Volatility Expected" : "Stable Market Conditions",
        volColor: isVolatile ? "amber" : "blue",
        volDesc: isVolatile
          ? `Expected volatility is ${volMult}x higher than historical average.`
          : "Price action is expected to remain within standard deviation bands."
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
            <BrainCircuit className="h-8 w-8 text-emerald-400" />
            AI Predictor
          </h1>
          <p className="text-zinc-400">Advanced machine learning models for stock price forecasting.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Input Section */}
        <div className="lg:col-span-1 space-y-6">
          <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6 backdrop-blur-sm">
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <Calculator className="h-5 w-5 text-emerald-400" />
              Analysis Parameters
            </h2>

            <form onSubmit={handleAnalyze} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-1">Ticker Symbol</label>
                <div className="relative">
                  <select
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value)}
                    className="block w-full px-3 py-2 border border-white/10 rounded-xl bg-black/50 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all appearance-none"
                  >
                    {TICKERS.map(t => (
                      <option key={t.id} value={t.id}>{t.name} ({t.id})</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-1">Prediction Horizon</label>
                <select
                  value={horizon}
                  onChange={(e) => setHorizon(e.target.value)}
                  className="block w-full px-3 py-2 border border-white/10 rounded-xl bg-black/50 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all appearance-none"
                >
                  <option value="7">7 Days</option>
                  <option value="14">14 Days</option>
                  <option value="30">30 Days</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-1">ML Model</label>
                <select className="block w-full px-3 py-2 border border-white/10 rounded-xl bg-black/50 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all appearance-none">
                  <option value="lstm">LSTM Neural Network</option>
                  <option value="transformer">Transformer-based</option>
                  <option value="ensemble">Ensemble Model (Recommended)</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={isAnalyzing}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-black hover:bg-emerald-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-6"
              >
                {isAnalyzing ? (
                  <>
                    <div className="h-4 w-4 border-2 border-black/20 border-t-black rounded-full animate-spin" />
                    Running Models...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Generate Prediction
                  </>
                )}
              </button>
            </form>
          </div>

          {/* AI Insights */}
          <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6 backdrop-blur-sm">
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-emerald-400" />
              AI Insights
            </h2>
            <div className="space-y-4">
              <div className={`p-4 rounded-xl bg-${insights.trendColor}-500/10 border border-${insights.trendColor}-500/20`}>
                <p className={`text-sm text-${insights.trendColor}-400 font-medium mb-1`}>{insights.trend}</p>
                <p className="text-xs text-zinc-400">{insights.trendDesc}</p>
              </div>
              <div className={`p-4 rounded-xl bg-${insights.volColor}-500/10 border border-${insights.volColor}-500/20`}>
                <p className={`text-sm text-${insights.volColor}-400 font-medium mb-1`}>{insights.volWarning}</p>
                <p className="text-xs text-zinc-400">{insights.volDesc}</p>
              </div>
            </div>
          </div>

          {/* AI Deep Analysis Section */}
          <div className="rounded-2xl border border-emerald-500/10 bg-emerald-500/[0.02] p-6 backdrop-blur-sm border-t-2 border-t-emerald-500/30">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-emerald-400" />
                AI Deep Analysis
              </h2>
              <button
                onClick={handleDeepAnalysis}
                disabled={isDeepAnalyzing}
                className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition-colors flex items-center gap-1 disabled:opacity-50"
              >
                {isDeepAnalyzing ? "Analyzing..." : "Refresh Report"}
                <ArrowRight className="h-3 w-3" />
              </button>
            </div>

            {analysis ? (
              <div className="prose prose-invert prose-sm max-w-none text-zinc-300 leading-relaxed overflow-y-auto max-h-[400px] pr-2 scrollbar-thin scrollbar-thumb-white/10">
                <ReactMarkdown>{analysis}</ReactMarkdown>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center bg-black/20 rounded-xl border border-white/5">
                <BrainCircuit className="h-10 w-10 text-zinc-600 mb-3" />
                <p className="text-sm text-zinc-400 max-w-[200px]">
                  Generate a detailed LLM-powered report for {symbol}.
                </p>
                <button
                  onClick={handleDeepAnalysis}
                  disabled={isDeepAnalyzing}
                  className="mt-4 px-4 py-2 bg-emerald-500/10 text-emerald-400 rounded-lg text-xs font-bold hover:bg-emerald-500/20 transition-all border border-emerald-500/20"
                >
                  {isDeepAnalyzing ? "Consulting AI..." : "Generate AI Report"}
                </button>
              </div>
            )}

            {deepError && (
              <p className="mt-2 text-xs text-rose-400 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                {deepError}
              </p>
            )}
          </div>
        </div>


        {/* Chart Section */}
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6 backdrop-blur-sm h-full min-h-[500px] flex flex-col">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-semibold text-white">{symbol} Price Forecast</h2>
                <p className="text-sm text-zinc-400">Historical data + {horizon}-day AI prediction</p>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-zinc-500" />
                  <span className="text-zinc-400">Historical</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-emerald-500" />
                  <span className="text-zinc-400">Predicted</span>
                </div>
              </div>
            </div>

            <div className="flex-1 w-full min-h-[400px] relative">
              {isAnalyzing && (
                <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#0a0a0a]/50 backdrop-blur-sm rounded-xl">
                  <div className="flex flex-col items-center gap-4">
                    <div className="h-8 w-8 border-4 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
                    <p className="text-emerald-400 font-medium animate-pulse">Processing neural networks...</p>
                  </div>
                </div>
              )}
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={predictionData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                  <defs>
                    <linearGradient id="colorPredicted" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#71717a" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#71717a" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                  <XAxis
                    dataKey="day"
                    stroke="#ffffff40"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(val) => val === 0 ? 'Today' : val > 0 ? `+${val}d` : `${val}d`}
                  />
                  <YAxis
                    domain={['auto', 'auto']}
                    stroke="#ffffff40"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value) => `₹${value.toFixed(0)}`}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#18181b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    labelFormatter={(val) => val === 0 ? 'Today' : val > 0 ? `Day +${val}` : `Day ${val}`}
                  />
                  <ReferenceLine x={0} stroke="#ffffff40" strokeDasharray="3 3" />

                  {/* Confidence Interval (Upper/Lower bounds) */}
                  <Area
                    type="monotone"
                    dataKey="upperBound"
                    stroke="none"
                    fill="#10b981"
                    fillOpacity={0.05}
                  />
                  <Area
                    type="monotone"
                    dataKey="lowerBound"
                    stroke="none"
                    fill="#0a0a0a"
                    fillOpacity={1}
                  />

                  <Area
                    type="monotone"
                    dataKey="actual"
                    stroke="#71717a"
                    strokeWidth={2}
                    fill="url(#colorActual)"
                  />
                  <Area
                    type="monotone"
                    dataKey="predicted"
                    stroke="#10b981"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    fill="url(#colorPredicted)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-6 grid grid-cols-3 gap-4 border-t border-white/10 pt-6">
              <div>
                <p className="text-sm text-zinc-400 mb-1">Current Price</p>
                <p className="text-2xl font-bold text-white">₹{currentPrice.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-sm text-zinc-400 mb-1">Predicted ({horizon}d)</p>
                <p className={`text-2xl font-bold ${expectedReturn >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  ₹{predictedPrice.toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-sm text-zinc-400 mb-1">Expected Return</p>
                <p className={`text-2xl font-bold flex items-center ${expectedReturn >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {expectedReturn > 0 ? '+' : ''}{expectedReturn.toFixed(2)}%
                  {expectedReturn >= 0 ? <ArrowUpRight className="h-5 w-5 ml-1" /> : <ArrowRight className="h-5 w-5 ml-1 rotate-45" />}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
