import { useState } from "react";

const contacts = [
    {
        icon: (
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z" />
            </svg>
        ),
        label: "Email",
        value: "info@yashilqollar.uz",
        href: "mailto:info@yashilqollar.uz",
    },
    {
        icon: (
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z" />
            </svg>
        ),
        label: "Telegram",
        value: "@tashkent_tech_mun",
        href: "https://t.me/tashkent_tech_mun",
    },
];

const faq = [
    {
        q: "Who can attend Yashil Qo'llar MUN 2026?",
        a: "Yashil Qo'llar MUN is open to high school and university students from all countries. No prior MUN experience is required for most committees.",
    },
    {
        q: "What language are committee sessions held in?",
        a: "All official committee sessions and communications are conducted in English.",
    },
    {
        q: "Is accommodation provided?",
        a: "We can recommend partner hotels near the venue. Details are sent to registered delegates upon confirmation.",
    },
    {
        q: "When will I receive committee and country assignments?",
        a: "Assignments are sent by email approximately 3–4 weeks before the conference begins.",
    },
    {
        q: "Can I attend as a delegation (school group)?",
        a: "Yes! We welcome school and university delegations. Please contact us for group registration discounts.",
    },
];

export const ContactPage = () => {
    const [openFaq, setOpenFaq] = useState<number | null>(null);

    return (
        <main className="min-h-screen pt-24 pb-20 px-6 bg-stone-950">
            <section className="max-w-7xl mx-auto">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 mb-24">
                    {/* Контакты */}
                    <div>
                        <h1 className="text-4xl font-montserrat font-black text-white mb-8 uppercase">Contact Us</h1>
                        <div className="space-y-4 mb-8">
                            {contacts.map((c, i) => (
                                <a
                                    key={i}
                                    href={c.href}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="group flex items-center gap-4 bg-white/[0.03] border border-white/5 p-4 rounded-2xl hover:border-emerald-500/20 transition-all"
                                >
                                    <div className="shrink-0 w-9 h-9 bg-white/5 border border-white/10 rounded-xl flex items-center justify-center text-white/40 group-hover:text-emerald-500 group-hover:border-emerald-500/20 transition-colors">
                                        {c.icon}
                                    </div>
                                    <div>
                                        <div className="text-[10px] font-bold tracking-[1.2px] uppercase font-montserrat text-white/30 mb-0.5">
                                            {c.label}
                                        </div>
                                        <div className="text-white/70 text-sm font-inter">{c.value}</div>
                                    </div>
                                </a>
                            ))}
                        </div>

                        {/* Location */}
                        <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 overflow-hidden">
                            <div className="text-[10px] font-bold tracking-[1.2px] uppercase font-montserrat text-white/30 mb-3">
                                Location
                            </div>
                            <div className="w-full h-40 bg-gradient-to-br from-emerald-500/5 to-transparent rounded-xl flex flex-col items-center justify-center border border-white/5 gap-2 text-center px-4">
                                <svg className="w-8 h-8 text-emerald-500/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                                </svg>
                                <span className="text-white/30 text-xs font-inter">
                                    Universitetskaya St. 2/1, Almazar, Tashkent
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* FAQ */}
                    <div>
                        <div className="text-center mb-10">
                            <span className="text-emerald-500 text-[10px] font-extrabold tracking-[2.5px] uppercase font-montserrat mb-4 block">
                                Quick Answers
                            </span>
                            <h2 className="font-montserrat font-black text-3xl text-white uppercase text-start">
                                Frequently Asked Questions
                            </h2>
                        </div>
                        <div className="space-y-3">
                            {faq.map((item, i) => (
                                <div
                                    key={i}
                                    className={`bg-white/[0.03] border rounded-2xl overflow-hidden transition-all ${openFaq === i ? "border-emerald-500/30" : "border-white/5"
                                        }`}
                                >
                                    <button
                                        onClick={() => setOpenFaq(openFaq === i ? null : i)}
                                        className="w-full flex items-center justify-between gap-4 px-6 py-5 text-left"
                                    >
                                        <span className="font-montserrat font-bold text-white text-sm">{item.q}</span>
                                        <span
                                            className={`shrink-0 w-6 h-6 rounded-full flex items-center justify-center transition-colors ${openFaq === i ? "bg-emerald-500/20 text-emerald-500" : "bg-white/5 text-white/30"
                                                }`}
                                        >
                                            {openFaq === i ? "−" : "+"}
                                        </span>
                                    </button>
                                    {openFaq === i && (
                                        <div className="px-6 pb-5">
                                            <p className="text-white/50 text-sm leading-relaxed font-inter">{item.a}</p>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </section>
        </main>
    );
};