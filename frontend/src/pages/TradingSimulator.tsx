import { useState, useEffect, useRef } from "react";
import {
    Play,
    Pause,
    RotateCcw,
    TrendingUp,
    TrendingDown,
    DollarSign,
    Clock,
    BarChart3,
    AlertCircle,
    Trophy,
    ArrowUpRight,
    ArrowDownRight,
    Gamepad2,
    ChevronRight,
    History
} from "lucide-react";
import {
    ResponsiveContainer,
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ReferenceLine
} from "recharts";

interface StockFile {
    filename: string;
    name: string;
    symbol: string;
}

interface OHLCV {
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
}

interface Trade {
    type: 'buy' | 'sell';
    price: number;
    shares: number;
    timestamp: string;
}

export default function TradingSimulator() {
    const API_BASE_URL = "http://localhost:8000/api";

    // Setup Session States
    const [stocks, setStocks] = useState<StockFile[]>([]);
    const [selectedStock, setSelectedStock] = useState<string>("");
    const [duration, setDuration] = useState<number>(30); // minutes
    const [isLoadingStocks, setIsLoadingStocks] = useState(true);
    const [gameState, setGameState] = useState<'setup' | 'playing' | 'result'>('setup');

    // Game Logic States
    const [fullData, setFullData] = useState<OHLCV[]>([]);
    const [visibleData, setVisibleData] = useState<OHLCV[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);
    const [speed, setSpeed] = useState(2000); // ms per tick

    // Portfolio States
    const [cash, setCash] = useState(100000); // Start with 1 Lakh
    const [shares, setShares] = useState(0);
    const [trades, setTrades] = useState<Trade[]>([]);
    const [pnl, setPnl] = useState(0);
    const [tradeAmount, setTradeAmount] = useState<number>(10);

    // Time States
    const [timeLeft, setTimeLeft] = useState(0);
    const [availableYears, setAvailableYears] = useState<number[]>([]);
    const [startYear, setStartYear] = useState<number | null>(null);
    const [endYear, setEndYear] = useState<number | null>(null);
    const [detectedInterval, setDetectedInterval] = useState<string>("");

    const timerRef = useRef<NodeJS.Timeout | null>(null);
    const tickRef = useRef<NodeJS.Timeout | null>(null);

    // Fetch stocks on mount
    useEffect(() => {
        fetchStocks();
    }, []);

    const fetchStocks = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/simulator/stocks`);
            const data = await response.json();
            setStocks(data.stocks || []);
            if (data.stocks && data.stocks.length > 0) {
                setSelectedStock(data.stocks[0].filename);
            }
        } catch (error) {
            console.error("Failed to fetch stocks:", error);
        } finally {
            setIsLoadingStocks(false);
        }
    };

    useEffect(() => {
        if (selectedStock) {
            fetchMetadata();
        }
    }, [selectedStock]);

    const fetchMetadata = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/simulator/metadata/${selectedStock}`);
            const data = await response.json();
            setAvailableYears(data.years || []);
            setDetectedInterval(data.interval || "");
            if (data.years && data.years.length > 0) {
                const latest = data.years[data.years.length - 1];
                setStartYear(latest);
                setEndYear(latest);
            }
        } catch (error) {
            console.error("Failed to fetch metadata:", error);
        }
    };

    const startSession = async () => {
        if (!selectedStock) return;

        setGameState('playing');
        setIsPlaying(true);
        setCash(100000);
        setShares(0);
        setTrades([]);
        setCurrentIndex(20); // Start with 20 points visible
        setTimeLeft(duration * 60);

        try {
            const url = `${API_BASE_URL}/simulator/data/${selectedStock}?start_year=${startYear}&end_year=${endYear}`;
            const response = await fetch(url);
            const data = await response.json();

            const points = data.data || [];
            if (points.length === 0) {
                alert("No data found for this year range. Try another range.");
                setGameState('setup');
                return;
            }
            setFullData(points);
            setVisibleData(points.slice(0, 20));

            // Adjust speed to fit data within duration: (duration in ms) / (points to show)
            const targetSpeed = Math.max(100, Math.floor((duration * 60 * 1000) / (points.length || 1)));
            setSpeed(targetSpeed);
        } catch (error) {
            console.error("Failed to fetch simulator data:", error);
        }
    };

    // Game Tick
    useEffect(() => {
        if (gameState === 'playing' && isPlaying) {
            tickRef.current = setInterval(() => {
                setCurrentIndex(prev => {
                    const next = prev + 1;
                    if (next >= fullData.length) {
                        endGame();
                        return prev;
                    }
                    setVisibleData(fullData.slice(0, next));
                    return next;
                });
            }, speed);
        } else {
            if (tickRef.current) clearInterval(tickRef.current);
        }
        return () => { if (tickRef.current) clearInterval(tickRef.current); };
    }, [gameState, isPlaying, fullData, speed]);

    // Session Timer
    useEffect(() => {
        if (gameState === 'playing' && isPlaying && timeLeft > 0) {
            timerRef.current = setInterval(() => {
                setTimeLeft(prev => {
                    if (prev <= 1) {
                        endGame();
                        return 0;
                    }
                    return prev - 1;
                });
            }, 1000);
        } else {
            if (timerRef.current) clearInterval(timerRef.current);
        }
        return () => { if (timerRef.current) clearInterval(timerRef.current); };
    }, [gameState, isPlaying, timeLeft]);

    const endGame = () => {
        setIsPlaying(false);
        setGameState('result');
    };

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const currentPrice = visibleData.length > 0 ? visibleData[visibleData.length - 1].close : 0;

    // Calculate P&L
    useEffect(() => {
        const portfolioValue = cash + (shares * currentPrice);
        setPnl(portfolioValue - 100000);
    }, [currentPrice, cash, shares]);

    const handleBuy = (count?: number) => {
        const buyCount = count || tradeAmount;
        if (buyCount <= 0) return;

        const totalCost = buyCount * currentPrice;
        if (cash >= totalCost) {
            setCash(prev => prev - totalCost);
            setShares(prev => prev + buyCount);
            setTrades(prev => [{
                type: 'buy',
                price: currentPrice,
                shares: buyCount,
                timestamp: visibleData[visibleData.length - 1].date
            }, ...prev]);
        }
    };

    const handleSell = (count?: number) => {
        const sellCount = count || tradeAmount;
        if (sellCount <= 0) return;

        if (shares >= sellCount) {
            const revenue = sellCount * currentPrice;
            setCash(prev => prev + revenue);
            setShares(prev => prev - sellCount);
            setTrades(prev => [{
                type: 'sell',
                price: currentPrice,
                shares: sellCount,
                timestamp: visibleData[visibleData.length - 1].date
            }, ...prev]);
        }
    };

    const handleBuyMax = () => {
        const maxShares = Math.floor(cash / currentPrice);
        if (maxShares > 0) handleBuy(maxShares);
    };

    const handleSellAll = () => {
        if (shares > 0) handleSell(shares);
    };

    if (gameState === 'setup') {
        return (
            <div className="max-w-4xl mx-auto py-12">
                <div className="text-center mb-12">
                    <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-400 mb-6 border border-emerald-500/20">
                        <Gamepad2 className="h-8 w-8" />
                    </div>
                    <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-zinc-500 mb-4">
                        Stock Trading Simulator
                    </h1>
                    <p className="text-zinc-400 text-lg">Test your intuition with real historical high-frequency data</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="space-y-6 p-8 rounded-3xl border border-white/5 bg-white/[0.02] backdrop-blur-sm">
                        <div>
                            <label className="block text-sm font-medium text-zinc-400 mb-3">Select Company</label>
                            <div className="grid grid-cols-1 gap-3">
                                {stocks.map(stock => (
                                    <button
                                        key={stock.filename}
                                        onClick={() => setSelectedStock(stock.filename)}
                                        className={`flex items-center justify-between p-4 rounded-xl border transition-all ${selectedStock === stock.filename
                                            ? "bg-emerald-500/10 border-emerald-500/50 text-emerald-400"
                                            : "bg-white/5 border-white/5 text-zinc-400 hover:bg-white/[0.08]"
                                            }`}
                                    >
                                        <div className="text-left">
                                            <div className="font-semibold text-white">
                                                {stock.filename.split('.')[0].replace('Dataset ', '').split('_')[0].split('.')[0].replace('Hindustan Zinc Limited', 'Hindustan Zinc')}
                                            </div>
                                            <div className="text-[10px] opacity-40 uppercase tracking-widest mt-0.5">
                                                {stock.filename.includes('5minute') ? '5m Intraday' : 'Daily Historical'}
                                            </div>
                                        </div>
                                        <ChevronRight className={`h-4 w-4 transition-transform ${selectedStock === stock.filename ? "translate-x-1" : "opacity-0"}`} />
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="space-y-6 flex flex-col justify-between">
                        <div className="p-8 rounded-3xl border border-white/5 bg-white/[0.02] backdrop-blur-sm">
                            <div className="flex items-center justify-between mb-4">
                                <label className="block text-sm font-medium text-zinc-400">Timeline & Interval</label>
                                {detectedInterval && (
                                    <span className="px-2 py-0.5 rounded bg-zinc-800 text-[10px] text-zinc-500 font-mono">
                                        DATA: {detectedInterval}
                                    </span>
                                )}
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <p className="text-[10px] text-zinc-600 uppercase tracking-widest mb-2">Select Year Range</p>
                                    <div className="flex flex-wrap gap-2 max-h-[120px] overflow-y-auto no-scrollbar pr-2">
                                        {availableYears.map(yr => {
                                            const isSelected = (startYear && endYear) ? (yr >= startYear && yr <= endYear) : (yr === startYear);
                                            return (
                                                <button
                                                    key={yr}
                                                    onClick={() => {
                                                        if (!startYear || (startYear && endYear && startYear !== endYear)) {
                                                            setStartYear(yr);
                                                            setEndYear(yr);
                                                        } else if (yr < startYear) {
                                                            setStartYear(yr);
                                                        } else {
                                                            setEndYear(yr);
                                                        }
                                                    }}
                                                    className={`px-3 py-1.5 rounded-lg border text-xs transition-all ${isSelected
                                                        ? "bg-emerald-500/10 border-emerald-500/50 text-emerald-400 font-bold"
                                                        : "bg-white/5 border-white/5 text-zinc-500 hover:text-zinc-300"
                                                        }`}
                                                >
                                                    {yr}
                                                </button>
                                            );
                                        })}
                                        {availableYears.length === 0 && <span className="text-xs text-zinc-600 italic">No year data available</span>}
                                    </div>
                                    {(startYear && endYear) && (
                                        <p className="mt-3 text-[10px] text-emerald-500/70 font-medium">
                                            SELECTED: {startYear} - {endYear}
                                        </p>
                                    )}
                                </div>

                                <div>
                                    <p className="text-[10px] text-zinc-600 uppercase tracking-widest mb-2">Session Duration</p>
                                    <div className="grid grid-cols-3 gap-2">
                                        {[1, 5, 15, 30, 45, 60].map(m => (
                                            <button
                                                key={m}
                                                onClick={() => setDuration(m)}
                                                className={`py-2 rounded-xl border text-xs font-medium transition-all ${duration === m
                                                    ? "bg-blue-500/10 border-blue-500/50 text-blue-400"
                                                    : "bg-white/5 border-white/5 text-zinc-500 hover:bg-white/[0.08]"
                                                    }`}
                                            >
                                                {m >= 60 ? `${m / 60}h` : `${m}m`}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <button
                            onClick={startSession}
                            disabled={isLoadingStocks || !selectedStock}
                            className="w-full flex items-center justify-center gap-3 py-6 rounded-3xl bg-emerald-500 text-black font-bold text-lg hover:bg-emerald-400 transition-all shadow-lg hover:shadow-emerald-500/20 disabled:opacity-50"
                        >
                            <Play className="h-6 w-6 " fill="currentColor" />
                            START TRADING
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    if (gameState === 'result') {
        const finalReturn = (pnl / 100000) * 100;
        return (
            <div className="max-w-xl mx-auto py-12 text-center animate-in fade-in zoom-in duration-500">
                <div className={`inline-flex h-20 w-20 items-center justify-center rounded-3xl mb-8 ${pnl >= 0 ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"}`}>
                    <Trophy className="h-10 w-10" />
                </div>
                <h1 className="text-4xl font-bold text-white mb-2">Session Complete!</h1>
                <p className="text-zinc-500 mb-12">Performance for {stocks.find(s => s.filename === selectedStock)?.name}</p>

                <div className="grid grid-cols-2 gap-4 mb-12 text-left">
                    <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                        <p className="text-xs text-zinc-500 uppercase tracking-widest mb-1">Total P&L</p>
                        <p className={`text-3xl font-bold ${pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                            ₹{pnl.toLocaleString()}
                        </p>
                    </div>
                    <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                        <p className="text-xs text-zinc-500 uppercase tracking-widest mb-1">Return</p>
                        <p className={`text-3xl font-bold ${pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                            {pnl >= 0 ? "+" : ""}{finalReturn.toFixed(2)}%
                        </p>
                    </div>
                </div>

                {/* Performance Comparison */}
                <div className="bg-white/5 border border-white/10 rounded-2xl p-6 text-left mb-6">
                    <p className="text-xs text-zinc-500 uppercase tracking-widest mb-4">Market Comparison</p>
                    <div className="space-y-4">
                        <div className="flex justify-between items-center text-sm">
                            <span className="text-zinc-400">Stock's Actual Move:</span>
                            {(() => {
                                const startPrice = fullData[0]?.close || 1;
                                const endPrice = fullData[currentIndex]?.close || startPrice;
                                const stockReturn = ((endPrice - startPrice) / startPrice) * 100;
                                return (
                                    <span className={stockReturn >= 0 ? "text-emerald-400" : "text-rose-400"}>
                                        {stockReturn >= 0 ? "+" : ""}{stockReturn.toFixed(2)}%
                                    </span>
                                );
                            })()}
                        </div>
                        <div className="flex justify-between items-center text-sm">
                            <span className="text-zinc-400">Your Performance:</span>
                            <span className={finalReturn >= 0 ? "text-emerald-400" : "text-rose-400"}>
                                {finalReturn >= 0 ? "+" : ""}{finalReturn.toFixed(2)}%
                            </span>
                        </div>
                        <div className="pt-2 border-t border-white/10 flex justify-between items-center font-bold">
                            <span className="text-zinc-300">Alpha (vs Market):</span>
                            {(() => {
                                const startPrice = fullData[0]?.close || 1;
                                const endPrice = fullData[currentIndex]?.close || startPrice;
                                const stockReturn = ((endPrice - startPrice) / startPrice) * 100;
                                const alpha = finalReturn - stockReturn;
                                return (
                                    <span className={alpha >= 0 ? "text-emerald-400" : "text-rose-400"}>
                                        {alpha >= 0 ? "+" : ""}{alpha.toFixed(2)}%
                                    </span>
                                );
                            })()}
                        </div>
                    </div>
                </div>

                <div className="bg-white/5 border border-white/10 rounded-2xl p-6 text-left mb-12">
                    <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                        <History className="h-4 w-4" /> Trade Summary
                    </h3>
                    <div className="space-y-3 max-h-[200px] overflow-y-auto pr-2">
                        {trades.length === 0 ? (
                            <p className="text-zinc-500 text-sm italic">No trades executed</p>
                        ) : trades.map((t, i) => (
                            <div key={i} className="flex justify-between items-center text-sm border-b border-white/5 pb-2 last:border-0">
                                <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${t.type === 'buy' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                                    {t.type}
                                </span>
                                <span className="text-zinc-400">{t.shares} shares @ ₹{t.price.toFixed(2)}</span>
                                <span className="text-zinc-500 text-[10px]">{t.timestamp.split(' ')[1]}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <button
                    onClick={() => setGameState('setup')}
                    className="flex items-center justify-center gap-2 w-full py-4 rounded-xl bg-white text-black font-semibold hover:bg-zinc-200 transition-all"
                >
                    <RotateCcw className="h-4 w-4" />
                    PLAY AGAIN
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <div className="flex items-center gap-3 mb-1">
                        <span className="text-2xl font-bold text-white uppercase">{stocks.find(s => s.filename === selectedStock)?.symbol}</span>
                        <span className="px-2 py-1 rounded text-[10px] bg-white/10 text-zinc-400 border border-white/5 font-mono">SIMULATED DATA</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-zinc-500">
                        <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> Ends in {formatTime(timeLeft)}</span>
                        <span className="flex items-center gap-1"><BarChart3 className="h-3 w-3" /> Interval: {detectedInterval}</span>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <div className="flex items-center bg-white/5 border border-white/10 rounded-xl p-1">
                        {[500, 1000, 2000, 5000].map(s => (
                            <button
                                key={s}
                                onClick={() => setSpeed(s)}
                                className={`px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all ${speed === s ? 'bg-emerald-500 text-black' : 'text-zinc-500 hover:text-white'}`}
                            >
                                {s === 500 ? '4X' : s === 1000 ? '2X' : s === 2000 ? '1X' : 'SLOW'}
                            </button>
                        ))}
                    </div>
                    <button
                        onClick={() => setIsPlaying(!isPlaying)}
                        className={`p-2.5 rounded-xl border border-white/10 transition-all ${isPlaying ? 'bg-rose-500/10 text-rose-500 hover:bg-rose-500/20' : 'bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20'}`}
                    >
                        {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" fill="currentColor" />}
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Main Chart */}
                <div className="lg:col-span-3 space-y-6">
                    <div className="bg-[#0c0c0c] border border-white/5 rounded-3xl p-6 min-h-[500px] flex flex-col backdrop-blur-sm">
                        <div className="flex items-center justify-between mb-8">
                            <div>
                                <p className="text-zinc-500 text-xs uppercase tracking-widest mb-1">Simulated Price</p>
                                <p className="text-4xl font-bold text-white flex items-baseline gap-2">
                                    ₹{currentPrice.toLocaleString()}
                                    <span className={`text-sm font-medium ${pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                        {pnl >= 0 ? '+' : ''}{pnl.toLocaleString()}
                                    </span>
                                </p>
                            </div>
                            <div className="text-right">
                                <p className="text-zinc-500 text-xs uppercase tracking-widest mb-1">Session Data</p>
                                <p className="text-zinc-400 font-mono text-sm">{visibleData[visibleData.length - 1]?.date}</p>
                            </div>
                        </div>

                        <div className="flex-1 w-full relative">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={visibleData}>
                                    <defs>
                                        <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor={pnl >= 0 ? "#10b981" : "#f43f5e"} stopOpacity={0.3} />
                                            <stop offset="95%" stopColor={pnl >= 0 ? "#10b981" : "#f43f5e"} stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                                    <XAxis
                                        dataKey="date"
                                        hide
                                    />
                                    <YAxis
                                        domain={['auto', 'auto']}
                                        orientation="right"
                                        stroke="#ffffff20"
                                        fontSize={10}
                                        tickLine={false}
                                        axisLine={false}
                                    />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#121212', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                                        labelStyle={{ color: '#71717a' }}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="close"
                                        stroke={pnl >= 0 ? "#10b981" : "#f43f5e"}
                                        strokeWidth={2}
                                        fillOpacity={1}
                                        fill="url(#colorPrice)"
                                        animationDuration={300}
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4">
                            <p className="text-zinc-500 text-[10px] uppercase tracking-widest mb-1">Open</p>
                            <p className="text-sm font-semibold text-white">₹{visibleData[visibleData.length - 1]?.open.toFixed(2)}</p>
                        </div>
                        <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4">
                            <p className="text-zinc-500 text-[10px] uppercase tracking-widest mb-1">High</p>
                            <p className="text-sm font-semibold text-emerald-400">₹{visibleData[visibleData.length - 1]?.high.toFixed(2)}</p>
                        </div>
                        <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4">
                            <p className="text-zinc-500 text-[10px] uppercase tracking-widest mb-1">Low</p>
                            <p className="text-sm font-semibold text-rose-400">₹{visibleData[visibleData.length - 1]?.low.toFixed(2)}</p>
                        </div>
                        <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4">
                            <p className="text-zinc-500 text-[10px] uppercase tracking-widest mb-1">Volume</p>
                            <p className="text-sm font-semibold text-zinc-300">{visibleData[visibleData.length - 1]?.volume.toLocaleString()}</p>
                        </div>
                    </div>
                </div>

                {/* Sidebar Controls */}
                <div className="space-y-6">
                    <div className="bg-[#0c0c0c] border border-white/5 rounded-3xl p-6 backdrop-blur-sm">
                        <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                            <DollarSign className="h-3 w-3" /> Your Portfolio
                        </h3>

                        <div className="space-y-4 mb-8">
                            <div>
                                <p className="text-zinc-500 text-[10px] uppercase tracking-widest mb-1">Cash Balance</p>
                                <p className="text-2xl font-bold text-white">₹{cash.toLocaleString()}</p>
                            </div>
                            <div>
                                <p className="text-zinc-500 text-[10px] uppercase tracking-widest mb-1">Stock Holdings</p>
                                <p className="text-xl font-bold text-zinc-300">{shares} <span className="text-xs font-normal">shares</span></p>
                            </div>
                            <div>
                                <p className="text-zinc-500 text-[10px] uppercase tracking-widest mb-1">Position Value</p>
                                <p className="text-xl font-bold text-zinc-300">₹{(shares * currentPrice).toLocaleString()}</p>
                            </div>
                        </div>

                        <div className="space-y-4 pt-4 border-t border-white/5">
                            <div>
                                <label className="text-zinc-500 text-[10px] uppercase tracking-widest mb-2 block">Shares to Trade</label>
                                <div className="flex bg-white/5 rounded-xl border border-white/10 p-1">
                                    <button
                                        onClick={() => setTradeAmount(Math.max(1, tradeAmount - 10))}
                                        className="px-3 py-2 text-zinc-400 hover:text-white transition-colors"
                                    >-</button>
                                    <input
                                        type="number"
                                        value={tradeAmount}
                                        onChange={(e) => setTradeAmount(Math.max(1, parseInt(e.target.value) || 0))}
                                        className="flex-1 bg-transparent text-center text-white font-bold focus:outline-none"
                                    />
                                    <button
                                        onClick={() => setTradeAmount(tradeAmount + 10)}
                                        className="px-3 py-2 text-zinc-400 hover:text-white transition-colors"
                                    >+</button>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <button
                                    onClick={() => handleBuy()}
                                    disabled={cash < currentPrice * tradeAmount}
                                    className="flex items-center justify-center gap-2 py-3 rounded-xl bg-emerald-500 text-black font-bold hover:bg-emerald-400 transition-all disabled:opacity-30 text-xs"
                                >
                                    BUY {tradeAmount}
                                </button>
                                <button
                                    onClick={() => handleSell()}
                                    disabled={shares < tradeAmount}
                                    className="flex items-center justify-center gap-2 py-3 rounded-xl border border-rose-500/50 text-rose-500 font-bold hover:bg-rose-500/10 transition-all disabled:opacity-30 text-xs"
                                >
                                    SELL {tradeAmount}
                                </button>
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <button
                                    onClick={handleBuyMax}
                                    disabled={cash < currentPrice}
                                    className="flex items-center justify-center gap-2 py-2 rounded-lg bg-white/5 text-zinc-400 hover:text-white transition-all text-[10px] font-bold uppercase"
                                >
                                    BUY MAX
                                </button>
                                <button
                                    onClick={handleSellAll}
                                    disabled={shares === 0}
                                    className="flex items-center justify-center gap-2 py-2 rounded-lg bg-white/5 text-zinc-400 hover:text-white transition-all text-[10px] font-bold uppercase"
                                >
                                    SELL ALL
                                </button>
                            </div>
                        </div>
                    </div>

                    <div className="bg-[#0c0c0c] border border-white/5 rounded-3xl p-6 backdrop-blur-sm">
                        <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                            <History className="h-3 w-3" /> Recent Trades
                        </h3>
                        <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
                            {trades.length === 0 ? (
                                <div className="flex flex-col items-center justify-center py-12 text-center">
                                    <AlertCircle className="h-8 w-8 text-zinc-700 mb-2" />
                                    <p className="text-zinc-600 text-[10px]">No activity yet</p>
                                </div>
                            ) : trades.map((t, i) => (
                                <div key={i} className="flex flex-col gap-1 p-3 rounded-xl bg-white/[0.02] border border-white/5">
                                    <div className="flex justify-between items-center">
                                        <span className={`text-[10px] font-bold uppercase ${t.type === 'buy' ? 'text-emerald-400' : 'text-rose-400'}`}>{t.type}</span>
                                        <span className="text-[10px] text-zinc-500 font-mono">{t.timestamp.split(' ')[1]}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-xs text-white">{t.shares} shares</span>
                                        <span className="text-xs text-zinc-300 font-medium">₹{t.price.toFixed(2)}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
