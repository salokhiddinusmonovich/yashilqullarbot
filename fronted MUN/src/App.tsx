import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { LanguageProvider } from "./contexts/LanguageContext";
import { Navbar } from "./sections/Navbar/Navbar";
import { Footer } from "./sections/Footer/Footer";
import { NotFoundPage } from "./sections/NotFoundPage/NotFoundPage";
import { HomePage } from "./pages/HomePage";
import { AboutPage } from "./pages/AboutPage";
import { CommitteesPage } from "./pages/CommitteesPage";
import { TeamPage } from "./pages/TeamPage";
import { SchedulePage } from "./pages/SchedulePage";
import { RegistrationPage } from "./pages/RegistrationPage";
import { SponsorsPage } from "./pages/SponsorsPage";
import { ContactPage } from "./pages/ContactPage";

const Layout = ({ children }: { children: React.ReactNode }) => (
  <div className="dark">
    <div className="min-h-screen bg-stone-950 text-white font-inter selection:bg-emerald-500/30">
      <Navbar />
      <div className="box-border">{children}</div>
      <Footer />
    </div>
  </div>
);

export const App = () => (
  <LanguageProvider>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout><HomePage /></Layout>} />
        <Route path="/about" element={<Layout><AboutPage /></Layout>} />
        <Route path="/committees" element={<Layout><CommitteesPage /></Layout>} />
        <Route path="/team" element={<Layout><TeamPage /></Layout>} />
        <Route path="/schedule" element={<Layout><SchedulePage /></Layout>} />
        <Route path="/registration" element={<Layout><RegistrationPage /></Layout>} />
        <Route path="/sponsors" element={<Layout><SponsorsPage /></Layout>} />
        <Route path="/contact" element={<Layout><ContactPage /></Layout>} />
        <Route path="*" element={<Layout><NotFoundPage /></Layout>} />
      </Routes>
    </BrowserRouter>
  </LanguageProvider>
);
