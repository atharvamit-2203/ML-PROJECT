import { useState, useEffect } from "react";
import { Link } from "react-router";
import { ArrowUpRight, ArrowDownRight, Activity, TrendingUp, DollarSign, BarChart3, ChevronRight } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

// Mock data generator for charts
const generateChartData = (startPrice: number, volatility: number, trend: number) => {
  let currentPrice = startPrice;
  return Array.from({ length: 365 }).map((_, i) => {
    const change = (Math.random() - 0.5) * volatility + trend;
    currentPrice = Math.max(0, currentPrice + change);
    return { time: `Day ${i}`, price: currentPrice };
  });
};

const STOCKS = [
  { symbol: "TATACHEM", name: "Tata Chemicals", domain: "Chemicals", price: 1025.50, change: 2.4, data: generateChartData(1000, 15, 2) },
  { symbol: "TATAMOTORS", name: "Tata Motors", domain: "Automobile", price: 985.20, change: -1.2, data: generateChartData(990, 20, -1) },
  { symbol: "SPARC", name: "Sun Pharma Adv.", domain: "Pharmaceuticals", price: 345.10, change: 5.8, data: generateChartData(320, 10, 5) },
  { symbol: "HDFCBANK", name: "HDFC Bank", domain: "Bank", price: 1450.75, change: -0.4, data: generateChartData(1460, 25, -2) },
  { symbol: "LT", name: "Larsen & Toubro", domain: "IT", price: 3650.40, change: 1.1, data: generateChartData(3600, 40, 5) },
  { symbol: "ADANIGREEN", name: "Adani Green", domain: "Energy", price: 1890.15, change: 3.8, data: generateChartData(1800, 50, 10) },
  { symbol: "HINDZINC", name: "Hindustan Zinc", domain: "Metal & Mining", price: 315.40, change: 0.8, data: generateChartData(310, 5, 1) },
  { symbol: "TITAN", name: "Titan Company", domain: "Retail/Consumer", price: 3780.90, change: -1.5, data: generateChartData(3800, 45, -5) }
];

export default function Dashboard() {
  const [mounted, setMounted] = useState(false);
  const [timeframe, setTimeframe] = useState('1D');
  const [selectedStock, setSelectedStock] = useState(STOCKS[1]); // Default to TATAMOTORS

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  const getTimeframeData = (data: any[], tf: string) => {
    switch(tf) {
      case '1H': return data.slice(-12);
      case '1D': return data.slice(-24);
      case '1W': return data.slice(-7);
      case '1M': return data.slice(-30);
      case '1Y': return data;
      default: return data.slice(-24);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      {/* Hero Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-white mb-2">Market Overview</h1>
          <p className="text-zinc-400">Real-time insights and AI-powered predictions.</p>
        </div>
        <Link 
          to="/predictor" 
          className="group flex items-center gap-2 rounded-full bg-emerald-500/10 px-5 py-2.5 text-sm font-medium text-emerald-400 hover:bg-emerald-500/20 transition-all border border-emerald-500/20"
        >
          <Activity className="h-4 w-4" />
          Launch AI Predictor
          <ChevronRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: "NIFTY 50", value: "22,493.55", change: "+0.85%", icon: TrendingUp, positive: true },
          { label: "SENSEX", value: "74,119.39", change: "+0.90%", icon: BarChart3, positive: true },
          { label: "INDIA VIX", value: "14.25", change: "-2.10%", icon: Activity, positive: false }
        ].map((stat) => (
          <div key={stat.label} className="rounded-2xl border border-white/5 bg-white/[0.02] p-6 backdrop-blur-sm">
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm font-medium text-zinc-400">{stat.label}</span>
              <div className={`p-2 rounded-lg ${stat.positive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                <stat.icon className="h-4 w-4" />
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-white tracking-tight">{stat.value}</span>
              <span className={`text-sm font-medium flex items-center ${stat.positive ? 'text-emerald-400' : 'text-rose-400'}`}>
                {stat.positive ? <ArrowUpRight className="h-3 w-3 mr-1" /> : <ArrowDownRight className="h-3 w-3 mr-1" />}
                {stat.change}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Main Chart Area */}
      <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6 backdrop-blur-sm">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold text-white">Market Trend ({selectedStock.symbol})</h2>
            <p className="text-sm text-zinc-400">Last {timeframe}</p>
          </div>
          <div className="flex items-center gap-2">
            {['1H', '1D', '1W', '1M', '1Y'].map((tf) => (
              <button 
                key={tf} 
                onClick={() => setTimeframe(tf)}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  timeframe === tf 
                    ? 'bg-white/10 text-white' 
                    : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/5'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={getTimeframeData(selectedStock.data, timeframe)}>
              <defs>
                <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
              <XAxis dataKey="time" stroke="#ffffff40" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis domain={['auto', 'auto']} stroke="#ffffff40" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(value) => `₹${value}`} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#18181b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                itemStyle={{ color: '#10b981' }}
              />
              <Area type="monotone" dataKey="price" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorPrice)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Watchlist */}
      <div>
        <h2 className="text-xl font-semibold text-white mb-4">Trending Assets</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {STOCKS.map((stock) => {
            const isPositive = stock.change >= 0;
            return (
              <div 
                key={stock.symbol} 
                onClick={() => setSelectedStock(stock)}
                className={`group rounded-2xl border p-5 transition-colors cursor-pointer ${
                  selectedStock.symbol === stock.symbol 
                    ? 'border-emerald-500/30 bg-emerald-500/[0.02]' 
                    : 'border-white/5 bg-white/[0.02] hover:bg-white/[0.04]'
                }`}
              >
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-lg font-bold text-white">{stock.symbol}</h3>
                    <p className="text-sm text-zinc-400">{stock.name} <span className="text-xs opacity-50">({stock.domain})</span></p>
                  </div>
                  <div className={`flex items-center gap-1 text-sm font-medium px-2 py-1 rounded-md ${isPositive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                    {isPositive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                    {Math.abs(stock.change)}%
                  </div>
                </div>
                <div className="flex justify-between items-end">
                  <span className="text-2xl font-semibold text-white tracking-tight">₹{stock.price.toFixed(2)}</span>
                  <div className="h-10 w-24">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={getTimeframeData(stock.data, '1M')}>
                        <Area 
                          type="monotone" 
                          dataKey="price" 
                          stroke={isPositive ? "#10b981" : "#f43f5e"} 
                          strokeWidth={2} 
                          fill="none" 
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
