import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { LoadingState } from "./components/UI";

const Dashboard = lazy(() => import("./pages/Dashboard").then((module) => ({ default: module.Dashboard })));
const SpendAnalysis = lazy(() => import("./pages/SpendAnalysis").then((module) => ({ default: module.SpendAnalysis })));
const CostOptimization = lazy(() => import("./pages/CostOptimization").then((module) => ({ default: module.CostOptimization })));
const AIAdvisor = lazy(() => import("./pages/AIAdvisor").then((module) => ({ default: module.AIAdvisor })));

export default function App() {
  return <BrowserRouter><Suspense fallback={<div className="p-8"><LoadingState label="Opening workspace…" /></div>}><Routes><Route element={<Layout />}><Route index element={<Dashboard />} /><Route path="spend" element={<SpendAnalysis />} /><Route path="optimization" element={<CostOptimization />} /><Route path="advisor" element={<AIAdvisor />} /></Route></Routes></Suspense></BrowserRouter>;
}
