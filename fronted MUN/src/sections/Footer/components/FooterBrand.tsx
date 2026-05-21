import logoImg from "../../../pages/photo_2025-10-08_22-18-51.jpg";


export const FooterBrand = () => {
    return (
        <div className="box-border caret-transparent gap-x-0 flex flex-col col-end-[-1] col-start-1 min-h-[auto] min-w-[auto] outline-[3px] gap-y-0 no-underline md:col-end-auto md:col-start-auto">
            <a
                href="/"
                className="items-center box-border caret-transparent gap-x-[9.6px] flex min-h-[auto] min-w-[auto] outline-[3px] gap-y-[9.6px] no-underline mb-[13.6px]"
            >
                <img
                    src={logoImg}
                    alt="Yashil Qo'llar MUN"
                    className="box-border caret-transparent h-[26px] max-w-full min-h-[auto] min-w-[auto] outline-[3px] no-underline align-baseline w-[26px]"
                />
                <span className="box-border caret-transparent block font-black tracking-[0.96px] min-h-[auto] min-w-[auto] outline-[3px] no-underline uppercase font-montserrat">
                    Yashil Qo'llar MUN
                </span>
            </a>
            <p className="box-border caret-transparent text-stone-500 text-[12.8px] leading-[20.48px] max-w-[260px] min-h-[auto] min-w-[auto] outline-[3px] no-underline mb-4">
                Tashkent Tech Model United Nations
            </p>
            <p className="items-center box-border caret-transparent gap-x-6 flex flex-wrap min-h-[auto] min-w-[auto] outline-[3px] gap-y-6 no-underline">
                <span className="bg-emerald-500/10 box-border caret-transparent text-emerald-500 block text-[9.92px] font-bold tracking-[0.992px] leading-[15.872px] min-h-[auto] min-w-[auto] outline-[3px] no-underline border border-emerald-500/20 px-3 py-[3.2px] rounded-[40px] border-solid font-montserrat">
                    May 31, 2026
                </span>
                <span className="box-border caret-transparent text-zinc-800 block text-[11.2px] leading-[17.92px] min-h-[auto] min-w-[auto] outline-[3px] no-underline">
                    ·
                </span>
                <span className="box-border caret-transparent text-neutral-700 block text-[11.52px] font-medium leading-[18.432px] min-h-[auto] min-w-[auto] outline-[3px] no-underline font-montserrat">
                    Tashkent, Uzbekistan
                </span>
            </p>
        </div>
    );
};