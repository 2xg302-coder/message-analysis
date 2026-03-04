import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import NewsFeed from './pages/NewsFeed';
import Trends from './pages/Trends';
import Watchlist from './pages/Watchlist';
import SeriesView from './pages/SeriesView';

const App = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<NewsFeed />} />
          <Route path="trends" element={<Trends />} />
          <Route path="watchlist" element={<Watchlist />} />
          <Route path="series" element={<SeriesView />} />
          <Route path="series/:tag" element={<SeriesView />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
