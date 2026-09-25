import React, {useEffect, useMemo, useState} from "react";
import {createRoot} from "react-dom/client";
import {LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, BarChart, Bar} from "recharts";
import "./styles.css";

const API = "http://localhost:8000/api";

function App() {
  const [summary,setSummary]=useState(null);
  const [reviews,setReviews]=useState([]);
  const [insights,setInsights]=useState([]);
  const [trends,setTrends]=useState([]);
  const [property,setProperty]=useState("All properties");
  const [sentiment,setSentiment]=useState("All");
  const [loading,setLoading]=useState(true);

  async function load(){
    setLoading(true);
    const qs = new URLSearchParams();
    if(property !== "All properties") qs.set("property",property);
    if(sentiment !== "All") qs.set("sentiment",sentiment.toLowerCase());
    const [s,r,i,t]=await Promise.all([
      fetch(`${API}/summary`).then(x=>x.json()),
      fetch(`${API}/reviews?${qs}`).then(x=>x.json()),
      fetch(`${API}/insights`).then(x=>x.json()),
      fetch(`${API}/trends`).then(x=>x.json())
    ]);
    setSummary(s); setReviews(r); setInsights(i); setTrends(t); setLoading(false);
  }
  useEffect(()=>{load()},[property,sentiment]);

  const properties = summary?.property_breakdown?.map(x=>x.property) || [];
  const negativeCount = reviews.filter(x=>x.sentiment==="negative").length;

  return <div className="app">
    <header>
      <div>
        <div className="eyebrow">AZZURRO HOTELS • OPERATIONS</div>
        <h1>Review Insights Dashboard</h1>
        <p>Monitor guest sentiment, property performance and recurring operational issues.</p>
      </div>
      <button onClick={load}>↻ Refresh data</button>
    </header>

    <section className="filters">
      <label>Property
        <select value={property} onChange={e=>setProperty(e.target.value)}>
          <option>All properties</option>{properties.map(p=><option key={p}>{p}</option>)}
        </select>
      </label>
      <label>Sentiment
        <select value={sentiment} onChange={e=>setSentiment(e.target.value)}>
          <option>All</option><option>Positive</option><option>Negative</option><option>Mixed</option>
        </select>
      </label>
      <div className="filter-note">Sample dataset • Current week is calculated from the data available locally.</div>
    </section>

    {loading ? <div className="loading">Loading dashboard…</div> : <>
      <section className="cards">
        <div className="card"><span>Current week rating</span><strong>{summary.current_week.average_rating || "—"}</strong><small>{summary.current_week.review_count} reviews</small></div>
        <div className="card"><span>Previous week rating</span><strong>{summary.previous_week.average_rating || "—"}</strong><small>{summary.previous_week.review_count} reviews</small></div>
        <div className="card"><span>Week-over-week</span><strong>{(summary.current_week.average_rating-summary.previous_week.average_rating).toFixed(2)}</strong><small>rating point change</small></div>
        <div className="card"><span>Negative reviews</span><strong>{negativeCount}</strong><small>in current view</small></div>
      </section>

      <section className="grid two">
        <div className="panel"><h2>Positive & negative trend</h2><ResponsiveContainer width="100%" height={270}>
          <LineChart data={trends}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="date"/><YAxis allowDecimals={false}/><Tooltip/><Line type="monotone" dataKey="positive"/><Line type="monotone" dataKey="negative"/></LineChart>
        </ResponsiveContainer></div>
        <div className="panel"><h2>Property rating breakdown</h2><ResponsiveContainer width="100%" height={270}>
          <BarChart data={summary.property_breakdown}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="property" hide/><YAxis domain={[0,10]}/><Tooltip/><Bar dataKey="average_rating"/></BarChart>
        </ResponsiveContainer></div>
        <div className="mini-list">{summary.property_breakdown.map(x=><div key={x.property}><span>{x.property}</span><b>{x.average_rating}</b></div>)}</div>
      </section>

      <section className="grid two">
        <div className="panel"><h2>Operational insights</h2>
          {insights.map(x=><div className="insight" key={x.topic}><div><b>{x.topic}</b><span>{x.count} negative review{x.count===1?"":"s"}</span></div><strong>{x.percentage}%</strong><div className="bar"><i style={{width:`${Math.min(x.percentage,100)}%`}}/></div></div>)}
          {!insights.length && <p>No negative-topic data in this view.</p>}
        </div>
        <div className="panel"><h2>Review feed</h2>
          <div className="feed">{reviews.map(r=><article key={r.id}><div className="review-head"><b>{r.property}</b><span>{r.date}</span></div><div className="rating">{r.rating}/10 · {r.sentiment}</div><p>{r.text}</p><div className="tags">{r.topics.map(t=><span key={t}>{t}</span>)}</div></article>)}</div>
        </div>
      </section>
    </>}
    <footer>Local trial implementation • No credentials stored • Scraper includes defensive error handling and de-duplication.</footer>
  </div>
}
createRoot(document.getElementById("root")).render(<App/>);
