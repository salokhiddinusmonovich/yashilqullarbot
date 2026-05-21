export const FooterSocialLinks = () => {
    return (
        <div className="items-center box-border caret-transparent gap-x-[8.8px] flex min-h-[auto] min-w-[auto] outline-[3px] gap-y-[8.8px] text-center no-underline md:text-start">
            <a
                href="https://www.instagram.com/tashkent.tech.mun/"
                aria-label="Instagram"
                className="items-center bg-white/0 box-border caret-transparent text-neutral-700 flex h-[30px] justify-center min-h-[auto] min-w-[auto] outline-[3px] text-center no-underline w-[30px] border rounded-[7px] border-solid border-white/10 md:text-start hover:text-emerald-500 hover:bg-emerald-500/10 hover:border-emerald-500/30"
            >
                <img
                    src="https://c.animaapp.com/mpbkoruiNSwSIb/assets/icon-8.svg"
                    alt="Icon"
                    className="box-border caret-transparent h-4 outline-[3px] text-center no-underline align-baseline w-4 md:text-start"
                />
            </a>
            <a
                href="https://t.me/tashkent_tech_mun"
                aria-label="Telegram"
                className="items-center bg-white/0 box-border caret-transparent text-neutral-700 flex h-[30px] justify-center min-h-[auto] min-w-[auto] outline-[3px] text-center no-underline w-[30px] border rounded-[7px] border-solid border-white/10 md:text-start hover:text-emerald-500 hover:bg-emerald-500/10 hover:border-emerald-500/30"
            >
                <img
                    src="https://c.animaapp.com/mpbkoruiNSwSIb/assets/icon-9.svg"
                    alt="Icon"
                    className="box-border caret-transparent h-4 outline-[3px] text-center no-underline align-baseline w-4 md:text-start"
                />
            </a>
        </div>
    );
};