import { Link } from "react-router-dom";

const committeeTiers = [
    {
        tier: "Main Committees",
        color: "from-emerald-600 to-orange-400",
        list: [
            { abbr: "UNGA", name: "General Assembly", desc: "Global policy and sustainable development." },
            { abbr: "UNSC", name: "Security Council", desc: "International peace and security maintenance." },
        ],
    },
    {
        tier: "Specialized Agencies",
        color: "from-blue-600 to-blue-400",
        list: [
            { abbr: "WHO", name: "World Health Org", desc: "Global health emergency preparedness." },
            { abbr: "ECOSOC", name: "Economic & Social", desc: "Digital economy and tech divide." },
        ],
    },
];

const perks = [
    {
        tier: "Bronze Partner",
        perks: ["Logo on website", "Social media mention", "Certificate of appreciation"],
    },
    {
        tier: "Silver Partner",
        perks: ["All Bronze perks", "Logo on delegate kits", "Opening ceremony mention", "Small booth space"],
    },
    {
        tier: "Gold Partner",
        perks: ["All Silver perks", "Keynote speech slot", "Full-page ad in booklet", "VIP dinner access"],
    },
];

export const SponsorsPage = () => {
    return (
        <main className="min-h-screen pt-24 bg-stone-950">
            {/* COMMITTEES SECTION */}
            <section className="max-w-7xl mx-auto px-6 pb-20">
                <div className="text-center mb-16">
                    <span className="text-emerald-500 text-[10px] font-extrabold tracking-[2.5px] uppercase font-montserrat mb-4 block">
                        Our Structure
                    </span>
                    <h2 className="font-montserrat font-black text-3xl md:text-5xl text-white uppercase mb-4">
                        Conference Councils
                    </h2>
                </div>

                {committeeTiers.map((tier) => (
                    <div key={tier.tier} className="mb-16">
                        <h3 className="text-white/20 font-montserrat font-bold text-xs uppercase tracking-[3px] mb-8 flex items-center gap-4">
                            {tier.tier}
                            <div className="h-px bg-white/5 flex-1" />
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                            {tier.list.map((s) => (
                                <div key={s.abbr} className="bg-white/[0.03] border border-white/5 rounded-2xl p-6 hover:border-white/10 transition-all">
                                    <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${tier.color} flex items-center justify-center font-montserrat font-black text-white text-lg mb-4`}>
                                        {s.abbr}
                                    </div>
                                    <div className="font-montserrat font-bold text-white text-base mb-2">
                                        {s.name}
                                    </div>
                                    <div className="text-white/40 text-xs leading-relaxed">
                                        {s.desc}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </section>

            {/* SPONSORSHIP PACKAGES */}
            <section className="py-20 border-t border-white/5 bg-white/[0.02]">
                <div className="max-w-5xl mx-auto px-5 md:px-8">
                    <div className="text-center mb-14">
                        <span className="text-emerald-500 text-[10px] font-extrabold tracking-[2.5px] uppercase font-montserrat mb-4 block">
                            Partner With Us
                        </span>
                        <h2 className="font-montserrat font-black text-3xl md:text-4xl text-white uppercase leading-tight mb-4">
                            Sponsorship Packages
                        </h2>
                        <p className="text-white/50 max-w-xl mx-auto font-inter text-sm leading-relaxed">
                            Reach 300+ delegates from 40+ countries and gain brand visibility
                            across Tashkent's most international academic event.
                        </p>
                    </div>

                    <div className="grid md:grid-cols-3 gap-6 mb-12">
                        {perks.map((p) => (
                            <div
                                key={p.tier}
                                className="bg-white/[0.03] border border-white/5 rounded-2xl p-6 hover:border-emerald-500/20 transition-all"
                            >
                                <div className="font-montserrat font-black text-white text-base mb-5 pb-4 border-b border-white/5">
                                    {p.tier}
                                </div>
                                <ul className="space-y-3">
                                    {p.perks.map((item) => (
                                        <li key={item} className="flex gap-2.5 text-sm text-white/50">
                                            <span className="shrink-0 w-4 h-4 rounded-full bg-emerald-500/20 flex items-center justify-center mt-0.5">
                                                <svg className="w-2.5 h-2.5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                                </svg>
                                            </span>
                                            {item}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        ))}
                    </div>

                    <div className="text-center">
                        <p className="text-white/40 mb-6 font-inter text-sm">
                            Interested in sponsoring Yashil Qo'llar MUN 2026?
                        </p>
                        <Link
                            to="/contact"
                            className="inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white text-[12px] font-bold tracking-[1.2px] uppercase px-8 py-4 rounded-xl font-montserrat shadow-[rgba(255,102,0,0.3)_0px_8px_32px_0px] transition-all"
                        >
                            Get in Touch
                        </Link>
                    </div>
                </div>
            </section>
        </main>
    );
};