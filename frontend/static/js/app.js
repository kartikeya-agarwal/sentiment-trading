// Sentiment Trading System - Frontend JavaScript

const API_BASE = '/api';

// Global variables
let currentTicker = '';
let currentChartsData = null;

// Search stock function
async function searchStock() {
    const ticker = document.getElementById('ticker-input').value.trim().toUpperCase();
    if (!ticker) {
        showError('Please enter a stock ticker');
        return;
    }
    
    currentTicker = ticker;
    showLoading(true);
    hideError();
    
    try {
        // Get recommendation
        const recommendationResponse = await fetch(`${API_BASE}/recommendation/${ticker}`);
        const recommendationData = await recommendationResponse.json();
        
        if (recommendationData.error) {
            showError(recommendationData.error);
            showLoading(false);
            return;
        }
        
        displayRecommendation(recommendationData);
        
        // Get charts data
        const chartsResponse = await fetch(`${API_BASE}/charts/${ticker}`);
        const chartsData = await chartsResponse.json();
        currentChartsData = chartsData;
        
        if (!chartsData.error) {
            renderCharts(chartsData);
        }
        
        // Get sentiment snippets
        const sentimentResponse = await fetch(`${API_BASE}/sentiment/${ticker}`);
        const sentimentData = await sentimentResponse.json();
        
        if (!sentimentData.error) {
            displaySentimentSnippets(sentimentData);
        }
        
        showLoading(false);
    } catch (error) {
        showError(`Error fetching data: ${error.message}`);
        showLoading(false);
    }
}

// Display recommendation
function displayRecommendation(data) {
    const card = document.getElementById('recommendation-card');
    const tickerEl = document.getElementById('recommendation-ticker');
    const signalEl = document.getElementById('signal');
    const confidenceEl = document.getElementById('confidence');
    const reasoningEl = document.getElementById('reasoning');
    
    const signal = data.signal;
    
    tickerEl.textContent = `Recommendation for ${data.ticker}`;
    
    // Display signal
    signalEl.textContent = signal.signal_type.toUpperCase();
    signalEl.className = `signal ${signal.signal_type}`;
    
    // Display confidence
    const confidencePercent = (signal.confidence * 100).toFixed(1);
    confidenceEl.textContent = `Confidence: ${confidencePercent}%`;
    
    // Display reasoning
    reasoningEl.textContent = signal.reasoning || 'No reasoning provided';
    
    card.style.display = 'block';
}

// Render charts
function renderCharts(data) {
    // Price chart with sentiment overlay
    if (data.market_data && data.market_data.length > 0) {
        renderPriceChart(data);
    }
    
    // Sentiment timeline
    if (data.sentiment_timeline && data.sentiment_timeline.length > 0) {
        renderSentimentChart(data);
    }
    
    document.getElementById('charts-section').style.display = 'block';
}

// Render price chart
function renderPriceChart(data) {
    const marketData = data.market_data;
    const dates = marketData.map(d => d.date);
    const opens = marketData.map(d => d.Open);
    const highs = marketData.map(d => d.High);
    const lows = marketData.map(d => d.Low);
    const closes = marketData.map(d => d.Close);
    const volumes = marketData.map(d => d.Volume);
    
    // Create candlestick chart
    const candlestick = {
        x: dates,
        open: opens,
        high: highs,
        low: lows,
        close: closes,
        type: 'candlestick',
        name: 'Price',
        increasing: {line: {color: '#10b981'}},
        decreasing: {line: {color: '#ef4444'}}
    };
    
    // Add moving averages if available
    const traces = [candlestick];
    
    if (data.indicators) {
        const indicators = data.indicators.full_data || [];
        if (indicators.length > 0) {
            const ma20 = indicators.map(d => d.MA_20).filter(v => v !== null);
            if (ma20.length > 0) {
                traces.push({
                    x: dates.slice(-ma20.length),
                    y: ma20,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'MA 20',
                    line: {color: '#f59e0b'}
                });
            }
            
            const ma50 = indicators.map(d => d.MA_50).filter(v => v !== null);
            if (ma50.length > 0) {
                traces.push({
                    x: dates.slice(-ma50.length),
                    y: ma50,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'MA 50',
                    line: {color: '#3b82f6'}
                });
            }
        }
    }
    
    const layout = {
        title: `${data.ticker} Price Chart`,
        xaxis: {title: 'Date'},
        yaxis: {title: 'Price ($)'},
        hovermode: 'x unified'
    };
    
    Plotly.newPlot('price-chart', traces, layout, {responsive: true});
}

// Render sentiment chart
function renderSentimentChart(data) {
    const sentimentData = data.sentiment_timeline;
    const dates = sentimentData.map(d => d.date);
    const scores = sentimentData.map(d => d.avg_sentiment_score || 0);
    
    const trace = {
        x: dates,
        y: scores,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Sentiment Score',
        line: {
            color: '#667eea',
            width: 2
        },
        fill: 'tozeroy',
        fillcolor: 'rgba(102, 126, 234, 0.2)'
    };
    
    const layout = {
        title: 'Sentiment Timeline',
        xaxis: {title: 'Date'},
        yaxis: {title: 'Sentiment Score (-1 to 1)', range: [-1, 1]},
        shapes: [{
            type: 'line',
            x0: dates[0],
            x1: dates[dates.length - 1],
            y0: 0,
            y1: 0,
            line: {color: 'gray', width: 1, dash: 'dash'}
        }]
    };
    
    Plotly.newPlot('sentiment-chart', [trace], layout, {responsive: true});
}

// Display sentiment snippets
function displaySentimentSnippets(data) {
    const snippetsList = document.getElementById('snippets-list');
    const mentions = data.recent_mentions || [];
    
    if (mentions.length === 0) {
        snippetsList.innerHTML = '<p>No recent mentions found.</p>';
        document.getElementById('sentiment-snippets').style.display = 'block';
        return;
    }
    
    snippetsList.innerHTML = mentions.map(mention => {
        const source = mention.source || 'unknown';
        const text = mention.text || '';
        const metadata = mention.metadata || {};
        
        let metadataText = '';
        if (source === 'reddit') {
            metadataText = `r/${metadata.subreddit || 'unknown'} • ${metadata.upvotes || 0} upvotes`;
        } else if (source === 'twitter') {
            metadataText = `@${metadata.author || 'unknown'} • ${metadata.likes || 0} likes • ${metadata.retweets || 0} retweets`;
        } else if (source === 'news') {
            metadataText = `${metadata.source || 'News'} • ${metadata.headline || ''}`;
        }
        
        return `
            <div class="snippet">
                <div class="snippet-source">${source.toUpperCase()} • ${metadataText}</div>
                <div class="snippet-text">${text}</div>
            </div>
        `;
    }).join('');
    
    document.getElementById('sentiment-snippets').style.display = 'block';
}

// Run backtest
async function runBacktest() {
    const ticker = document.getElementById('backtest-ticker').value.trim().toUpperCase();
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    if (!ticker || !startDate || !endDate) {
        showError('Please fill in all backtest fields');
        return;
    }
    
    showLoading(true);
    hideError();
    
    try {
        const response = await fetch(`${API_BASE}/backtest`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ticker: ticker,
                start_date: startDate,
                end_date: endDate
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            showLoading(false);
            return;
        }
        
        displayBacktestResults(data);
        showLoading(false);
    } catch (error) {
        showError(`Error running backtest: ${error.message}`);
        showLoading(false);
    }
}

// Display backtest results
function displayBacktestResults(data) {
    const resultsDiv = document.getElementById('backtest-results');
    const metricsDiv = document.getElementById('backtest-metrics');
    
    // Display metrics
    const metrics = [
        {label: 'Total Return', value: `${data.total_return.toFixed(2)}%`},
        {label: 'Sharpe Ratio', value: data.sharpe_ratio ? data.sharpe_ratio.toFixed(2) : 'N/A'},
        {label: 'Max Drawdown', value: `${data.max_drawdown.toFixed(2)}%`},
        {label: 'Win Rate', value: `${data.win_rate.toFixed(2)}%`},
        {label: 'S&P 500 Return', value: `${data.sp500_return.toFixed(2)}%`},
        {label: 'vs S&P 500', value: `${data.vs_sp500_performance.toFixed(2)}%`}
    ];
    
    metricsDiv.innerHTML = metrics.map(metric => `
        <div class="metric">
            <div class="metric-label">${metric.label}</div>
            <div class="metric-value">${metric.value}</div>
        </div>
    `).join('');
    
    // Render performance chart
    if (data.daily_values && data.daily_values.length > 0) {
        renderPerformanceChart(data);
    }
    
    resultsDiv.style.display = 'block';
}

// Render performance comparison chart
function renderPerformanceChart(data) {
    const dailyValues = data.daily_values || [];
    const dates = dailyValues.map(d => d.date);
    const portfolioValues = dailyValues.map(d => d.value);
    
    // Calculate returns
    const initialValue = data.initial_capital;
    const portfolioReturns = portfolioValues.map(v => ((v - initialValue) / initialValue) * 100);
    
    // S&P 500 returns (if available)
    // Note: In a full implementation, you'd fetch S&P 500 data for comparison
    const sp500Returns = portfolioReturns.map((_, i) => {
        // Simplified: assuming linear S&P 500 return
        // In production, fetch actual S&P 500 data
        return (data.sp500_return / portfolioReturns.length) * (i + 1);
    });
    
    const traces = [
        {
            x: dates,
            y: portfolioReturns,
            type: 'scatter',
            mode: 'lines',
            name: 'Strategy',
            line: {color: '#667eea', width: 2}
        },
        {
            x: dates,
            y: sp500Returns,
            type: 'scatter',
            mode: 'lines',
            name: 'S&P 500',
            line: {color: '#10b981', width: 2, dash: 'dash'}
        }
    ];
    
    const layout = {
        title: 'Performance Comparison',
        xaxis: {title: 'Date'},
        yaxis: {title: 'Return (%)'},
        hovermode: 'x unified'
    };
    
    Plotly.newPlot('performance-chart', traces, layout, {responsive: true});
}

// Utility functions
function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
}

function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

function hideError() {
    document.getElementById('error').style.display = 'none';
}

// Allow Enter key to search
document.getElementById('ticker-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        searchStock();
    }
});

