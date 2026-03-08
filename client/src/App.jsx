import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import NewsFeed from './pages/NewsFeed';
import ITHomeView from './pages/ITHomeView';
import Trends from './pages/Trends';
import Watchlist from './pages/Watchlist';
import SeriesView from './pages/SeriesView';
import DataExplorer from './pages/DataExplorer';
import CalendarView from './pages/CalendarView';
import StorylineView from './pages/StorylineView';
import ErrorBoundary from './components/ErrorBoundary';

const App = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<NewsFeed />} />
          <Route path="ithome" element={<ITHomeView />} />
          <Route path="storylines" element={<StorylineView />} />
          <Route path="explorer" element={<DataExplorer />} />
          <Route path="trends" element={<Trends />} />
          <Route path="calendar" element={<CalendarView />} />
          <Route path="watchlist" element={<Watchlist />} />
          <Route path="series" element={
            <ErrorBoundary>
              <SeriesView />
            </ErrorBoundary>
          } />
          <Route path="series/:tag" element={
            <ErrorBoundary>
              <SeriesView />
            </ErrorBoundary>
          } />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
