import { Link } from "react-router-dom";

type EventType = "opening" | "committee" | "social" | "break" | "closing";

interface Event {
    time: string;
    title: string;
    subtitle?: string;
    type: EventType;
    location?: string;
}

interface DaySchedule {
    day: string;
    date: string;
    events: Event[];
}

const schedule: DaySchedule[] = [
    {
        day: "Day 1",
        date: "May 22, 2026",
        events: [
            { time: "09:00 – 10:30", title: "Opening Ceremony", subtitle: "Keynote speeches and formal introduction", type: "opening", location: "Main Auditorium" },
            { time: "11:00 – 13:00", title: "Committee Session I", subtitle: "Setting the agenda and opening statements", type: "committee", location: "Committee Rooms" },
            { time: "13:00 – 14:00", title: "Networking Lunch", type: "break", location: "Dining Hall" },
            { time: "19:00 – 21:00", title: "Delegate Social", subtitle: "Evening mixer and cultural performance", type: "social", location: "Grand Ballroom" },
        ],
    },
    {
        day: "Day 3",
        date: "May 24, 2026",
        events: [
            {
                time: "09:00 – 11:00",
                title: "Committee Session VI",
                subtitle: "Final debates and passage of resolutions",
                type: "committee",
                location: "Committee Rooms",
            },
            { time: "11:00 – 11:20", title: "Coffee Break", type: "break" },
            {
                time: "11:20 – 13:00",
                title: "Crisis Simulation",
                subtitle: "Special joint committee emergency session",
                type: "committee",
                location: "Main Auditorium",
            },
            {
                time: "13:00 – 14:00",
                title: "Lunch Break",
                type: "break",
                location: "Dining Hall",
            },
            {
                time: "14:00 – 15:30",
                title: "Press Conference",
                subtitle: "Committee chairs present adopted resolutions to media",
                type: "opening",
                location: "Media Room",
            },
            {
                time: "15:30 – 17:00",
                title: "Closing Ceremony",
                subtitle: "Best Delegate awards, sponsor recognition, closing remarks",
                type: "closing",
                location: "Main Auditorium",
            },
            {
                time: "17:00 – 19:00",
                title: "Farewell Reception",
                subtitle: "Celebrate with delegates, staff, and guests",
                type: "social",
                location: "University Gardens",
            },
        ],
    },
];

const typeStyles: Record<
    EventType,
    { dot: string; bg: string; label: string }
> = {
    opening: {
        dot: "bg-blue-400",
        bg: "border-blue-500/20 bg-blue-500/5",
        label: "Ceremony",
    },
    committee: {
        dot: "bg-emerald-500",
        bg: "border-emerald-500/20 bg-emerald-500/5",
        label: "Committee",
    },
    social: {
        dot: "bg-emerald-400",
        bg: "border-emerald-500/20 bg-emerald-500/5",
        label: "Social",
    },
    break: {
        dot: "bg-white/20",
        bg: "border-white/5 bg-white/[0.02]",
        label: "Break",
    },
    closing: {
        dot: "bg-purple-400",
        bg: "border-purple-500/20 bg-purple-500/5",
        label: "Closing",
    },
};

export const SchedulePage = () => {
    return (
        <main className="min-h-screen pt-24 pb-10 bg-stone-950">
            <section className="max-w-4xl mx-auto px-6">
                <div className="text-center mb-16">
                    <span className="text-emerald-500 text-[10px] font-extrabold tracking-[2.5px] uppercase font-montserrat mb-4 block">
                        Conference Timeline
                    </span>
                    <h1 className="font-montserrat font-black text-4xl md:text-5xl text-white uppercase mb-4">
                        Official Schedule
                    </h1>
                </div>

                <div className="space-y-16">
                    {schedule.map((day, dayIdx) => (
                        <div key={dayIdx}>
                            <div className="flex items-baseline gap-4 mb-8 border-b border-white/5 pb-4">
                                <h2 className="font-montserrat font-black text-2xl text-white uppercase">
                                    {day.day}
                                </h2>
                                <span className="text-white/30 text-sm font-inter">{day.date}</span>
                            </div>

                            <div className="space-y-3">
                                {day.events.map((ev, i) => {
                                    const s = typeStyles[ev.type];
                                    return (
                                        <div
                                            key={i}
                                            className={`flex gap-4 md:gap-6 items-start border rounded-2xl px-5 py-4 transition-all ${s.bg}`}
                                        >
                                            <div className="shrink-0 mt-1.5">
                                                <span className={`block w-2.5 h-2.5 rounded-full ${s.dot}`} />
                                            </div>
                                            <div className="shrink-0 w-36 hidden sm:block">
                                                <span className="font-montserrat font-bold text-white/60 text-xs tracking-wide">
                                                    {ev.time}
                                                </span>
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <span className="sm:hidden font-montserrat font-bold text-white/40 text-[10px] tracking-wide block mb-0.5">
                                                    {ev.time}
                                                </span>
                                                <div className="font-montserrat font-bold text-white text-sm md:text-base">
                                                    {ev.title}
                                                </div>
                                                {ev.subtitle && (
                                                    <div className="text-white/40 text-sm mt-0.5 font-inter">
                                                        {ev.subtitle}
                                                    </div>
                                                )}
                                            </div>
                                            {ev.location && (
                                                <div className="shrink-0 hidden md:flex items-center gap-1.5 text-white/30 text-xs font-inter">
                                                    <span>📍</span>
                                                    <span>{ev.location}</span>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            <section className="py-16 mt-20 border-t border-white/5">
                <div className="max-w-3xl mx-auto px-5 md:px-8 text-center">
                    <h2 className="font-montserrat font-black text-2xl md:text-3xl text-white uppercase leading-tight mb-4">
                        Ready to Join Us?
                    </h2>
                    <p className="text-white/50 mb-8 font-inter leading-relaxed">
                        Secure your spot at Yashil Qo'llar MUN 2026 and be part of three unforgettable
                        days of debate, diplomacy, and discovery.
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