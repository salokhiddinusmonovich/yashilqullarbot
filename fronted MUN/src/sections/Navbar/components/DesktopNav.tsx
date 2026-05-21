import { NavLink } from "react-router-dom";

const linkClass = ({ isActive }: { isActive: boolean }) =>
    `box-border caret-transparent inline text-[11.68px] font-semibold tracking-[1.168px] leading-[18.688px] min-h-0 min-w-0 outline-[3px] relative no-underline uppercase text-nowrap py-[3.2px] font-inter md:block md:min-h-[auto] md:min-w-[auto] transition-colors ${isActive ? "text-emerald-500" : "text-white/40 hover:text-white/90"}`;

export const DesktopNav = () => {
    return (
        <nav className="items-center box-border caret-transparent gap-x-[19.2px] hidden basis-[0%] grow justify-center min-h-0 min-w-0 outline-[3px] gap-y-[19.2px] no-underline md:flex md:min-h-[auto] md:min-w-[auto]">
            <NavLink to="/" end className={linkClass}>
                Home
            </NavLink>
            <NavLink to="/about" className={linkClass}>
                About
            </NavLink>
            <NavLink to="/committees" className={linkClass}>
                Committees
            </NavLink>
            <NavLink to="/team" className={linkClass}>
                Team
            </NavLink>
            <NavLink to="/schedule" className={linkClass}>
                Schedule
            </NavLink>
            <NavLink to="/registration" className={linkClass}>
                Register Now
            </NavLink>
            <NavLink to="/sponsors" className={linkClass}>
                Sponsors
            </NavLink>
            <NavLink to="/contact" className={linkClass}>
                Contact
            </NavLink>
        </nav>
    );
};