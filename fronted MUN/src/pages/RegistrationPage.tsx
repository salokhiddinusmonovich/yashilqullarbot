import { useState } from "react";

const fees = [
    {
        type: "Early Bird",
        deadline: "April 15, 2026",
        price: "$25",
        desc: "Full conference access, delegate kit, all meals, social events",
        badge: "Best Value",
        badgeColor: "bg-green-500/10 text-green-400 border-green-500/20",
    },
    {
        type: "Regular",
        deadline: "May 15, 2026",
        price: "$35",
        desc: "Full conference access, delegate kit, all meals, social events",
        badge: "",
        badgeColor: "",
    },
    {
        type: "On-Site",
        deadline: "May 31, 2026",
        price: "$45",
        desc: "Full conference access (no kit guarantee, limited seats)",
        badge: "Limited",
        badgeColor: "bg-red-500/10 text-red-400 border-red-500/20",
    },
];

const committees = [
    "UNSC",
    "UNGA",
    "WHO",
    "ECOSOC",
    "UNHRC",
    "ICJ",
    "DISEC",
    "SPECPOL",
];

export const RegistrationPage = () => {
    const [form, setForm] = useState({
        firstName: "",
        lastName: "",
        email: "",
        university: "",
        country: "",
        committee1: "",
        committee2: "",
        experience: "",
        motivation: "",
    });
    const [submitted, setSubmitted] = useState(false);

    const handleChange = (
        e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
    ) => {
        setForm({ ...form, [e.target.name]: e.target.value });
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitted(true);
    };

    return (
        <main className="min-h-screen pt-24 pb-20 px-6 bg-stone-950">
            <section className="max-w-5xl mx-auto">
                <div className="text-center mb-16">
                    <span className="text-emerald-500 text-[10px] font-extrabold tracking-[2.5px] uppercase font-montserrat mb-4 block">
                        Join the Conference
                    </span>
                    <h1 className="font-montserrat font-black text-4xl md:text-5xl text-white uppercase mb-4">
                        Delegate Registration
                    </h1>
                </div>

                {submitted ? (
                    <div className="bg-white/[0.03] border border-emerald-500/20 rounded-3xl p-12 text-center">
                        <div className="w-16 h-16 bg-emerald-500/20 text-emerald-500 rounded-full flex items-center justify-center mx-auto mb-6">
                            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                            </svg>
                        </div>
                        <h2 className="text-2xl font-montserrat font-bold text-white mb-2">Application Received!</h2>
                        <p className="text-white/40 mb-8">Thank you for applying. Our team will review your application and contact you via email.</p>
                        <button
                            onClick={() => setSubmitted(false)}
                            className="text-emerald-500 font-bold uppercase text-xs tracking-widest hover:text-orange-400 transition-colors"
                        >
                            Submit another application
                        </button>
                    </div>
                ) : (
                    <div>
                        <div className="mb-12">
                            <h2 className="font-montserrat font-black text-2xl text-white uppercase mb-8">Registration Fees</h2>
                            <div className="grid md:grid-cols-3 gap-5">
                                {fees.map((f) => (
                                    <div key={f.type} className="bg-white/[0.03] border border-white/5 rounded-2xl p-6 hover:border-emerald-500/20 transition-all relative">
                                        {f.badge && (
                                            <span className={`absolute top-4 right-4 text-[9px] font-bold tracking-[1px] uppercase font-montserrat px-2.5 py-1 rounded-full border ${f.badgeColor}`}>
                                                {f.badge}
                                            </span>
                                        )}
                                        <div className="font-montserrat font-black text-3xl text-emerald-500 mb-1">{f.price}</div>
                                        <div className="font-montserrat font-bold text-white text-base mb-1">{f.type}</div>
                                        <div className="text-white/30 text-xs mb-4">Deadline: {f.deadline}</div>
                                        <div className="text-white/40 text-sm leading-relaxed">{f.desc}</div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <form onSubmit={handleSubmit} className="bg-white/[0.03] border border-white/5 rounded-3xl p-8 md:p-10 space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div>
                                    <label className="text-[10px] font-bold tracking-[1.5px] uppercase font-montserrat text-white/40 block mb-2">First Name</label>
                                    <input type="text" name="firstName" required value={form.firstName} onChange={handleChange} className="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-3 text-sm font-inter outline-none focus:border-emerald-500/50 transition-all" />
                                </div>
                                <div>
                                    <label className="text-[10px] font-bold tracking-[1.5px] uppercase font-montserrat text-white/40 block mb-2">Last Name</label>
                                    <input type="text" name="lastName" required value={form.lastName} onChange={handleChange} className="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-3 text-sm font-inter outline-none focus:border-emerald-500/50 transition-all" />
                                </div>
                            </div>

                            <div>
                                <label className="text-[10px] font-bold tracking-[1.5px] uppercase font-montserrat text-white/40 block mb-2">Email Address</label>
                                <input type="email" name="email" required value={form.email} onChange={handleChange} className="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-3 text-sm font-inter outline-none focus:border-emerald-500/50 transition-all" />
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div>
                                    <label className="text-[10px] font-bold tracking-[1.5px] uppercase font-montserrat text-white/40 block mb-2">1st Committee Preference</label>
                                    <select name="committee1" required value={form.committee1} onChange={handleChange} className="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-3 text-sm font-inter outline-none focus:border-emerald-500/50 transition-all">
                                        <option value="" className="bg-zinc-900">Select committee</option>
                                        {committees.map((c) => (
                                            <option key={c} value={c} className="bg-zinc-900">{c}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label className="text-[10px] font-bold tracking-[1.5px] uppercase font-montserrat text-white/40 block mb-2">2nd Committee Preference</label>
                                    <select name="committee2" required value={form.committee2} onChange={handleChange} className="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-3 text-sm font-inter outline-none focus:border-emerald-500/50 transition-all">
                                        <option value="" className="bg-zinc-900">Select committee</option>
                                        {committees.map((c) => (
                                            <option key={c} value={c} className="bg-zinc-900">{c}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div>
                                <label className="text-[10px] font-bold tracking-[1.5px] uppercase font-montserrat text-white/40 block mb-2">MUN Experience</label>
                                <select name="experience" required value={form.experience} onChange={handleChange} className="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-3 text-sm font-inter outline-none focus:border-emerald-500/50 transition-all">
                                    <option value="" className="bg-zinc-900">Select experience level</option>
                                    <option value="none" className="bg-zinc-900">No prior MUN experience</option>
                                    <option value="1-2" className="bg-zinc-900">1–2 conferences</option>
                                    <option value="3-5" className="bg-zinc-900">3–5 conferences</option>
                                    <option value="5+" className="bg-zinc-900">5+ conferences</option>
                                </select>
                            </div>

                            <div>
                                <label className="text-[10px] font-bold tracking-[1.5px] uppercase font-montserrat text-white/40 block mb-2">Motivation Statement</label>
                                <textarea name="motivation" required value={form.motivation} onChange={handleChange} rows={4} placeholder="Why do you want to participate?" className="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-3 text-sm font-inter outline-none focus:border-emerald-500/50 transition-all resize-none" />
                            </div>

                            <button type="submit" className="w-full bg-emerald-500 hover:bg-emerald-600 text-white text-[12px] font-black tracking-[1.5px] uppercase py-4 rounded-xl font-montserrat shadow-[rgba(255,102,0,0.3)_0px_8px_32px_0px] transition-all">
                                Submit Application
                            </button>
                        </form>
                    </div>
                )}
            </section>
        </main>
    );
};