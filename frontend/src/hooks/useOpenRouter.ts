import { useState } from 'react';
import { getStockAnalysis } from '../services/openrouter';

export function useOpenRouter() {
    const [analysis, setAnalysis] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchAnalysis = async (symbol: string, currentPrice: number, predictedPrice: number, change: number) => {
        setLoading(true);
        setError(null);
        try {
            const result = await getStockAnalysis(symbol, currentPrice, predictedPrice, change);
            setAnalysis(result);
        } catch (err) {
            setError("Failed to fetch AI analysis. Check API key and network connectivity.");
        } finally {
            setLoading(false);
        }
    };

    return { analysis, loading, error, fetchAnalysis };
}
