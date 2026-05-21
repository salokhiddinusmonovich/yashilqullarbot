import React from "react";

const secretariat = [
    { name: "Jasur Jumaev", role: "Secretary-General", bio: "Leading the vision and overall management of Yashil Qo'llar MUN 2026." },
    { name: "Malika Rasulova", role: "Director-General", bio: "In charge of administrative operations and coordination." },
    { name: "Davron Azizov", role: "Under-Secretary-General", bio: "Overseeing committee chair training and academic quality." },
    { name: "Elena Kim", role: "Charge d'Affaires", bio: "Managing external relations and international delegations." },
];

const depts = [
    {
        name: "Information Technology",
        color: "text-emerald-500",
        bg: "bg-emerald-500/10",
        border: "border-emerald-500/20",
        members: [
            { name: "Farrukh Nabiev", role: "Tech Lead" },
            { name: "Otabek Aliev", role: "Full-stack Dev" },
            { name: "Sardor Ismoilov", role: "DevOps Engineer" },
            { name: "Nilufar Ganieva", role: "UI/UX Designer" },
        ],
    },
    {
        name: "Public Relations",
        color: "text-blue-500",
        bg: "bg-blue-500/10",
        border: "border-blue-500/20",
        members: [
            { name: "Kamola Akramova", role: "Head of PR" },
            { name: "Aziz Begmatov", role: "Social Media" },
            { name: "Diyora Usmanova", role: "Copywriter" },
            { name: "Timur Khan", role: "Media Outreach" },
        ],
    },
];

export const TeamPage = () => {
    return (
        <main className="min-h-screen pt-24 bg-stone-950">
            {/* SECRETARIAT SECTION */}
            <section className="max-w-6xl mx-auto px-5 md:px-8 py-16">
                <div className="text-center mb-16">
                    <span className="text-emerald-500 text-[10px] font-extrabold tracking-[2.5px] uppercase font-montserrat mb-4 block">
                        The Leadership
                    </span>
                    <h2 className="font-montserrat font-black text-2xl md:text-3xl text-white uppercase">
                        Secretariat
                    </h2>
                </div>

                <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-5">
                    {secretariat.map((m) => (
                        <div
                            key={m.name}
                            className="group bg-white/[0.03] border border-white/5 rounded-2xl p-6 hover:border-emerald-500/20 hover:bg-emerald-500/5 transition-all"
                        >
                            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-amber-400 flex items-center justify-center font-montserrat font-black text-xl text-white mb-4">
                                {m.name.charAt(0)}
                            </div>
                            <div className="font-montserrat font-bold text-white text-base mb-1">
                                {m.name}
                            </div>
                            <div className="text-emerald-500 text-[10px] font-bold tracking-[1px] uppercase font-montserrat mb-3">
                                {m.role}
                            </div>
                            <p className="text-white/40 text-xs leading-relaxed">{m.bio}</p>
                        </div>
                    ))}
                </div>
            </section>

            {/* DEPARTMENTS SECTION */}
            <section className="pb-24 max-w-6xl mx-auto px-5 md:px-8">
                <div className="text-center mb-12">
                    <h2 className="font-montserrat font-black text-xl md:text-2xl text-white uppercase opacity-50">
                        Support Departments
                    </h2>
                </div>
                <div className="space-y-10">
                    {depts.map((dept) => (
                        <div
                            key={dept.name}
                            className="bg-white/[0.02] border border-white/5 rounded-3xl p-6 md:p-8"
                        >
                            <div className="flex items-center gap-3 mb-6">
                                <div
                                    className={`w-2 h-8 rounded-full bg-gradient-to-b ${dept.color.replace("text", "bg")} to-stone-800`}
                                ></div>
                                <h3
                                    className={`font-montserrat font-black text-lg uppercase tracking-wide ${dept.color}`}
                                >
                                    {dept.name}
                                </h3>
                            </div>
                            <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-4">
                                {dept.members.map((m) => (
                                    <div
                                        key={m.name}
                                        className={`${dept.bg} border ${dept.border} rounded-xl p-4 transition-transform hover:scale-[1.02]`}
                                    >
                                        <div
                                            className={`w-9 h-9 rounded-xl flex items-center justify-center font-montserrat font-black text-sm text-white mb-3 bg-gradient-to-br from-stone-700 to-stone-600`}
                                        >
                                            {m.name.charAt(0)}
                                        </div>
                                        <div className="font-montserrat font-bold text-white text-sm mb-1">
                                            {m.name}
                                        </div>
                                        <div
                                            className={`text-[10px] font-semibold tracking-[0.5px] ${dept.color} opacity-80`}
                                        >
                                            {m.role}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </section>
        </main>
    );
};