import { Link } from "react-router-dom";

const values = [
    {
        icon: "⚖️",
        title: "Diplomacy",
        desc: "We believe in the power of dialogue and peaceful negotiation as the cornerstone of international relations.",
    },
    {
        icon: "🧠",
        title: "Critical Thinking",
        desc: "Delegates are encouraged to research deeply, challenge assumptions, and think beyond conventional viewpoints.",
    },
    {
        icon: "🌐",
        title: "Global Citizenship",
        desc: "We foster an understanding of interconnected global challenges and cultivate responsibility toward humanity.",
    },
    {
        icon: "🚀",
        title: "Youth Leadership",
        desc: "Yashil Qo'llar MUN empowers the next generation of leaders with skills that extend far beyond the conference hall.",
    },
];

const timeline = [
    {
        year: "2020",
        event: "Yashil Qo'llar MUN Founded",
        desc: "The first edition was held at Tashkent State Technical University with 80 delegates.",
    },
    {
        year: "2021",
        event: "Going Regional",
        desc: "Expanded to include delegates from Uzbekistan, Kazakhstan, and Kyrgyzstan.",
    },
    {
        year: "2022",
        event: "International Recognition",
        desc: "Gained recognition from NMUN and established partnerships with universities abroad.",
    },
    {
        year: "2023",
        event: "150+ Delegates",
        desc: "A milestone edition with participants from 25+ countries.",
    },
    {
        year: "2024",
        event: "Flagship Conference",
        desc: "Yashil Qo'llar MUN became the largest MUN conference in Central Asia.",
    },
    {
        year: "2026",
        event: "Yashil Qo'llar MUN 2026",
        desc: "300+ delegates, 8 committees, 40+ countries — our most ambitious edition yet.",
    },
];

export const AboutPage = () => {
    return (
        <main className="min-h-screen bg-stone-950 pt-20">
            {/* HERO SECTION */}
            <section className="py-20 px-6">
                <div className="max-w-4xl mx-auto text-center">
                    <span className="text-emerald-500 text-[10px] font-extrabold tracking-[2.5px] uppercase font-montserrat mb-4 block">
                        About the Conference
                    </span>
                    <h1 className="font-montserrat font-black text-4xl md:text-6xl text-white uppercase leading-tight mb-8">
                        Shaping the Future <br /> Through <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 to-amber-400">Diplomacy</span>
                    </h1>
                </div>
            </section>

            {/* WHAT IS MUN */}
            <section className="py-16 md:py-24 border-y border-white/5 bg-white/[0.02]">
                <div className="max-w-6xl mx-auto px-5 md:px-8">
                    <div className="grid md:grid-cols-2 gap-12 md:gap-20 items-center">
                        <div>
                            <span className="text-emerald-500 text-[10px] font-extrabold tracking-[2.5px] uppercase font-montserrat mb-4 block">
                                The Conference
                            </span>
                            <h2 className="font-montserrat font-black text-3xl md:text-4xl text-white uppercase leading-tight mb-6">
                                What is Model UN?
                            </h2>
                            <p className="text-white/50 leading-relaxed mb-4 font-inter">
                                Model United Nations (MUN) is an educational simulation where
                                students role-play as delegates to the United Nations.
                                Participants research real-world issues, represent countries,
                                debate solutions, and draft resolutions in committee sessions
                                that mirror actual UN meetings.
                            </p>
                            <p className="text-white/50 leading-relaxed mb-4 font-inter">
                                MUN develops essential 21st-century skills: public speaking,
                                negotiation, research, collaborative problem-solving,
                                cross-cultural communication, and leadership.
                            </p>
                            <p className="text-white/50 leading-relaxed font-inter">
                                Tashkent Tech MUN brings this globally proven educational model
                                to Central Asia, making world-class diplomatic training
                                accessible to students across the region.
                            </p>
                        </div>
                        <div className="space-y-4">
                            {[
                                { step: "01", title: "Country Assignment", desc: "Each delegate is assigned a country to represent across committee sessions." },
                                { step: "02", title: "Research & Preparation", desc: "Delegates research their country's position on the committee's agenda topics." },
                                { step: "03", title: "Debate & Negotiation", desc: "In committees, delegates deliver speeches, negotiate, and form blocs." },
                                { step: "04", title: "Resolution Drafting", desc: "Delegates collaborate to draft and vote on resolutions to address global issues." },
                            ].map((item) => (
                                <div key={item.step} className="flex gap-5 items-start">
                                    <div className="shrink-0 w-10 h-10 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center justify-center font-montserrat font-black text-emerald-500 text-sm">
                                        {item.step}
                                    </div>
                                    <div>
                                        <div className="font-montserrat font-bold text-white text-sm mb-1">{item.title}</div>
                                        <div className="text-white/40 text-sm leading-relaxed">{item.desc}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </section>

            {/* ABOUT TSTU */}
            <section className="py-16 md:py-24">
                <div className="max-w-6xl mx-auto px-5 md:px-8">
                    <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-8 md:p-12">
                        <div className="grid md:grid-cols-2 gap-10 items-center">
                            <div>
                                <span className="text-emerald-500 text-[10px] font-extrabold tracking-[2.5px] uppercase font-montserrat mb-4 block">
                                    Our Home
                                </span>
                                <h2 className="font-montserrat font-black text-2xl md:text-3xl text-white uppercase leading-tight mb-6">
                                    Tashkent State Technical University
                                </h2>
                                <p className="text-white/50 leading-relaxed mb-4 font-inter">
                                    Founded in 1929, Tashkent State Technical University (TSTU) is
                                    Uzbekistan's leading engineering and technology institution.
                                </p>
                                <p className="text-white/50 leading-relaxed font-inter">
                                    Located in the heart of Tashkent, TSTU provides a world-class venue for
                                    international dialogue and academic excellence.
                                </p>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                {[
                                    { value: "1929", label: "Founded" },
                                    { value: "30,000+", label: "Students" },
                                    { value: "50+", label: "Faculties" },
                                    { value: "Top 3", label: "In Uzbekistan" },
                                ].map((item) => (
                                    <div key={item.label} className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 text-center">
                                        <div className="font-montserrat font-black text-2xl text-emerald-500 mb-1">{item.value}</div>
                                        <div className="text-white/40 text-[11px] font-semibold tracking-[1px] uppercase font-montserrat">{item.label}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* VALUES */}
            <section className="py-16 md:py-24 bg-white/[0.02] border-y border-white/5">
                <div className="max-w-6xl mx-auto px-5 md:px-8">
                    <div className="text-center mb-14">
                        <span className="text-emerald-500text-[10px] font-extrabold tracking-[2.5px] uppercase font-montserrat mb-4 block">
                            Our Philosophy
                        </span>
                        <h2 className="font-montserrat font-black text-3xl md:text-4xl text-white uppercase leading-tight">
                            What We Stand For
                        </h2>
                    </div>
                    <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
                        {values.map((v) => (
                            <div key={v.title} className="bg-white/[0.03] border border-white/5 rounded-2xl p-6 hover:border-emerald-500/20 hover:bg-emerald-500/5 transition-all">
                                <div className="text-3xl mb-4">{v.icon}</div>
                                <h3 className="font-montserrat font-bold text-white text-base mb-3">{v.title}</h3>
                                <p className="text-white/40 text-sm leading-relaxed">{v.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* TIMELINE */}
            <section className="py-16 md:py-24">
                <div className="max-w-4xl mx-auto px-5 md:px-8">
                    <div className="text-center mb-14">
                        <span className="text-emerald-500 text-[10px] font-extrabold tracking-[2.5px] uppercase font-montserrat mb-4 block">
                            Our Journey
                        </span>
                        <h2 className="font-montserrat font-black text-3xl md:text-4xl text-white uppercase leading-tight">
                            History of Yashil Qo'llar MUN
                        </h2>
                    </div>
                    <div className="relative">
                        <div className="absolute left-[19px] md:left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-emerald-500/50 to-transparent"></div>
                        <div className="space-y-8">
                            {timeline.map((item, i) => (
                                <div key={item.year} className={`relative flex gap-6 md:gap-0 ${i % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse"}`}>
                                    <div className="shrink-0 w-10 h-10 bg-emerald-500 rounded-full flex items-center justify-center z-10 md:absolute md:left-1/2 md:-translate-x-1/2 md:top-0 shadow-[0_0_15px_rgba(249,115,22,0.5)]">
                                        <div className="w-3 h-3 bg-white rounded-full"></div>
                                    </div>
                                    <div className={`md:w-[calc(50%-40px)] ${i % 2 === 0 ? "md:pr-10 md:text-right" : "md:pl-10 md:ml-auto"}`}>
                                        <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 hover:border-emerald-500/20 transition-all">
                                            <div className="text-emerald-500 font-montserrat font-black text-sm mb-1">{item.year}</div>
                                            <div className="font-montserrat font-bold text-white mb-2">{item.event}</div>
                                            <div className="text-white/40 text-sm leading-relaxed">{item.desc}</div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="py-16 border-t border-white/5">
                <div className="max-w-3xl mx-auto px-5 md:px-8 text-center">
                    <h2 className="font-montserrat font-black text-2xl md:text-3xl text-white uppercase leading-tight mb-4">
                        Be Part of the Story
                    </h2>
                    <p className="text-white/50 mb-8 font-inter leading-relaxed">
                        Join hundreds of delegates who will gather in Tashkent to shape
                        their futures through diplomacy.
                    </p>
                    <Link
                        to="/registration"
                        className="inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white text-[12px] font-bold tracking-[1.2px] uppercase px-8 py-4 rounded-xl font-montserrat shadow-[rgba(255,102,0,0.3)_0px_8px_32px_0px] transition-all"
                    >
                        Register for Yashil Qo'llar MUN 2026
                    </Link>
                </div>
            </section>
        </main>
    );
};