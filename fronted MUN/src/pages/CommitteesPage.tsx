import { useState } from "react";

// Массив данных комитетов
const committees = [
    {
        code: "WHO",
        name: "World Health Organization",
        level: "Intermediate",
        size: "40",
        topic1: "Global pandemic preparedness and vaccine equity",
        topic2: "Mental health crisis in conflict-affected regions",
        chair: "Dr. Alisher Erkinov",
        desc: "WHO delegates tackle the world's most pressing public health challenges. A strong background in health policy and scientific literacy will be advantageous in this committee.",
        color: "from-blue-600 to-cyan-500",
    },
    {
        code: "ECOSOC",
        name: "Economic and Social Council",
        level: "Intermediate",
        size: "35",
        topic1: "Digital economy and bridging the technological divide",
        topic2: "Gender equality and women's economic empowerment in developing nations",
        chair: "Rustam Khasanov",
        desc: "ECOSOC coordinates the economic, social, and related work of 14 UN specialized agencies. Delegates will debate policies on sustainable development, poverty reduction, and social equity.",
        color: "from-green-700 to-emerald-500",
    },
    {
        code: "UNHRC",
        name: "UN Human Rights Council",
        level: "Intermediate – Advanced",
        size: "30",
        topic1: "Human rights implications of artificial intelligence and surveillance technologies",
        topic2: "Protecting the rights of climate refugees and internally displaced persons",
        chair: "Sabina Mirzayeva",
        desc: "The UNHRC is responsible for promoting and protecting human rights globally. Expect passionate debate on sensitive issues requiring careful, evidence-based argumentation.",
        color: "from-purple-700 to-violet-500",
    },
    {
        code: "ICJ",
        name: "International Court of Justice",
        level: "Advanced",
        size: "20",
        topic1: "State responsibility for cyberattacks on critical infrastructure",
        topic2: "Jurisdiction over crimes against humanity in failed states",
        chair: "Otabek Nazarov",
        desc: "The ICJ simulates proceedings of the principal judicial organ of the United Nations. Delegates serve as judges and legal advocates, presenting oral arguments and applying international law.",
        color: "from-amber-700 to-yellow-500",
    },
    {
        code: "DISEC",
        name: "Disarmament & International Security Committee",
        level: "Beginner – Intermediate",
        size: "45",
        topic1: "Non-proliferation of nuclear weapons and the NPT regime",
        topic2: "Autonomous weapons systems and the ethics of lethal AI in warfare",
        chair: "Feruza Alimova",
        desc: "DISEC (First Committee of the UNGA) deals with disarmament and matters related to international security. This committee is well-suited for delegates with an interest in geopolitics and defense policy.",
        color: "from-slate-600 to-gray-500",
    },
    {
        code: "SPECPOL",
        name: "Special Political & Decolonization Committee",
        level: "Beginner",
        size: "50",
        topic1: "Post-colonial reparations and historical accountability",
        topic2: "The situation in occupied and disputed territories worldwide",
        chair: "Javokhir Ergashev",
        desc: "SPECPOL (Fourth Committee) covers a unique combination of political topics — particularly those related to decolonization. Its broad mandate makes it an excellent committee for new delegates.",
        color: "from-teal-700 to-cyan-600",
    },
];

const levelColors: Record<string, string> = {
    Beginner: "bg-green-500/10 text-green-400 border-green-500/20",
    "Beginner – Intermediate": "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
    Intermediate: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    "Intermediate – Advanced": "bg-emerald-500/10 text-orange-400 border-emerald-500/20",
    Advanced: "bg-red-500/10 text-red-400 border-red-500/20",
};

export const CommitteesPage = () => {
    const [selected, setSelected] = useState<string | null>(null);

    return (
        <main className="min-h-screen pt-24 pb-20 px-6">
            <section className="max-w-7xl mx-auto">
                <h1 className="text-4xl font-montserrat font-black text-white mb-12">Committees</h1>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {committees.map((c) => (
                        <div
                            key={c.code}
                            className={`bg-white/[0.03] border rounded-2xl overflow-hidden transition-all cursor-pointer ${selected === c.code ? "border-emerald-500/40" : "border-white/5 hover:border-white/10"
                                }`}
                            onClick={() => setSelected(selected === c.code ? null : c.code)}
                        >
                            <div className="p-6">
                                <div className="flex items-start justify-between gap-4 mb-4">
                                    <div
                                        className={`inline-flex items-center justify-center bg-gradient-to-br ${c.color} text-white text-[10px] font-black tracking-[1px] uppercase font-montserrat px-3 py-1.5 rounded-lg`}
                                    >
                                        {c.code}
                                    </div>
                                    <div className="flex items-center gap-2 flex-wrap justify-end">
                                        <span
                                            className={`text-[9px] font-bold tracking-[1px] uppercase font-montserrat px-2.5 py-1 rounded-full border ${levelColors[c.level] || ""
                                                }`}
                                        >
                                            {c.level}
                                        </span>
                                        <span className="text-[9px] font-bold tracking-[1px] uppercase font-montserrat px-2.5 py-1 rounded-full border bg-white/5 border-white/10 text-white/40">
                                            {c.size} seats
                                        </span>
                                    </div>
                                </div>
                                <h3 className="font-montserrat font-bold text-white text-base mb-3">{c.name}</h3>
                                <div className="space-y-2">
                                    <div className="flex gap-2">
                                        <span className="shrink-0 w-5 h-5 bg-emerald-500/10 rounded-md flex items-center justify-center text-emerald-500 text-[10px] font-black font-montserrat mt-0.5">
                                            1
                                        </span>
                                        <p className="text-white/40 text-sm leading-relaxed">{c.topic1}</p>
                                    </div>
                                    <div className="flex gap-2">
                                        <span className="shrink-0 w-5 h-5 bg-white/5 rounded-md flex items-center justify-center text-white/30 text-[10px] font-black font-montserrat mt-0.5">
                                            2
                                        </span>
                                        <p className="text-white/30 text-sm leading-relaxed">{c.topic2}</p>
                                    </div>
                                </div>
                                <div className="mt-4 flex items-center justify-between">
                                    <div className="flex items-center gap-2 text-white/30 text-xs">
                                        <span>Chair:</span>
                                        <span className="text-white/50 font-semibold">{c.chair}</span>
                                    </div>
                                    <span className="text-emerald-500 text-[11px] font-bold tracking-[1px] uppercase font-montserrat">
                                        {selected === c.code ? "▲ Less" : "▼ More"}
                                    </span>
                                </div>
                            </div>
                            {selected === c.code && (
                                <div className="px-6 pb-6 border-t border-white/5 pt-5">
                                    <p className="text-white/50 text-sm leading-relaxed">{c.desc}</p>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </section>
        </main>
    );
};