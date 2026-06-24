import React from "react";
import {
  Outlet,
  NavLink,
  Navigate,
  Link,
  useNavigate,
  useLocation,
} from "react-router";
import {
  Target,
  LayoutDashboard,
  Settings,
  Users,
  ClipboardList,
  Briefcase,
  Sparkles,
  Plus,
  User,
  LogOut,
  ChevronsUpDown,
  MoreHorizontal,
  ArrowUp,
  ArrowDown,
  Trash2,
  AlertTriangle,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupAction,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
  useSidebar,
} from "./ui/sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "./ui/alert-dialog";
import { Separator } from "./ui/separator";
import { useProfile } from "../lib/profile";
import { useAuth } from "../lib/auth";
import { useGoals, UserGoal } from "../lib/goals";
import { NotificationsButton } from "./NotificationsButton";
import { NotificationOrchestrator } from "./NotificationOrchestrator";

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "U";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

const navItems = [
  { to: "/", end: true, label: "Dashboard", icon: LayoutDashboard },
  { to: "/applications", label: "Applications", icon: ClipboardList },
  { to: "/ai-coaching", label: "AI Coaching", icon: Sparkles },
  { to: "/jobs", label: "Jobs", icon: Briefcase },
  { to: "/alumni", label: "Network", icon: Users, avatar: true },
] as const;

function AlumniNavAvatar() {
  return (
    <span
      className="relative flex size-4 shrink-0 items-center justify-center"
      aria-hidden="true"
    >
      <span className="absolute left-0 top-0 size-2.5 rounded-full bg-blue-500" />
      <span className="absolute right-0 top-0 size-2.5 rounded-full bg-cyan-500" />
      <span className="absolute bottom-0 left-1/2 size-2.5 -translate-x-1/2 rounded-full border border-sidebar bg-indigo-500" />
    </span>
  );
}

function AppSidebar({
  displayName,
  email,
  onLogout,
  onRequestDeleteGoal,
}: {
  displayName: string;
  email: string;
  onLogout: () => void;
  onRequestDeleteGoal: (goal: UserGoal) => void;
}) {
  const location = useLocation();
  const { isMobile, setOpenMobile } = useSidebar();
  const { goals, reorderGoals } = useGoals();

  const closeOnMobile = () => {
    if (isMobile) setOpenMobile(false);
  };

  const isActive = (to: string, end?: boolean) =>
    end ? location.pathname === to : location.pathname.startsWith(to);

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild tooltip="AI Career Helper">
              <NavLink to="/" onClick={closeOnMobile}>
                <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-blue-600">
                  <Target className="size-4 text-white" />
                </div>
                <span className="truncate font-semibold tracking-tight">
                  AI Career Helper
                </span>
              </NavLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.to}>
                  <SidebarMenuButton
                    asChild
                    tooltip={item.label}
                    isActive={isActive(item.to, "end" in item ? item.end : false)}
                  >
                    <NavLink to={item.to} onClick={closeOnMobile}>
                      {"avatar" in item ? <AlumniNavAvatar /> : <item.icon />}
                      <span>{item.label}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Career Goals</SidebarGroupLabel>
          <SidebarGroupAction asChild title="Add a career goal">
            <Link to="/new-goal" onClick={closeOnMobile}>
              <Plus />
              <span className="sr-only">Add a career goal</span>
            </Link>
          </SidebarGroupAction>
          <SidebarGroupContent>
            <SidebarMenu>
              {goals.length === 0 ? (
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    tooltip="Add your first goal"
                    className="text-sidebar-foreground/60"
                  >
                    <Link to="/new-goal" onClick={closeOnMobile}>
                      <Plus />
                      <span>Add your first goal</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ) : (
                goals.map((goal, idx) => (
                  <SidebarMenuItem key={goal.id}>
                    <SidebarMenuButton
                      asChild
                      tooltip={goal.title}
                      isActive={isActive(`/career-goal/${goal.id}`)}
                    >
                      <NavLink
                        to={`/career-goal/${goal.id}`}
                        onClick={closeOnMobile}
                      >
                        <div
                          className={`flex size-4 shrink-0 items-center justify-center rounded-[5px] bg-gradient-to-br ${goal.color}`}
                        >
                          <Target className="size-3 text-white" />
                        </div>
                        <span>{goal.title}</span>
                      </NavLink>
                    </SidebarMenuButton>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <SidebarMenuAction
                          showOnHover
                          aria-label={`Manage ${goal.title}`}
                        >
                          <MoreHorizontal />
                        </SidebarMenuAction>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent
                        side={isMobile ? "bottom" : "right"}
                        align="start"
                        className="w-44"
                      >
                        <DropdownMenuItem
                          disabled={idx === 0}
                          onSelect={() => reorderGoals(idx, idx - 1)}
                        >
                          <ArrowUp className="h-4 w-4" />
                          Move up
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          disabled={idx === goals.length - 1}
                          onSelect={() => reorderGoals(idx, idx + 1)}
                        >
                          <ArrowDown className="h-4 w-4" />
                          Move down
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          variant="destructive"
                          onSelect={() => onRequestDeleteGoal(goal)}
                        >
                          <Trash2 className="h-4 w-4" />
                          Delete goal
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </SidebarMenuItem>
                ))
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton
                  size="lg"
                  className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                >
                  <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white">
                    {initialsOf(displayName)}
                  </div>
                  <div className="grid flex-1 text-left text-sm leading-tight">
                    <span className="truncate font-semibold">{displayName}</span>
                    <span className="truncate text-xs text-muted-foreground">
                      {email}
                    </span>
                  </div>
                  <ChevronsUpDown className="ml-auto size-4" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                side={isMobile ? "bottom" : "right"}
                align="end"
                className="w-56"
              >
                <DropdownMenuLabel className="flex flex-col gap-0.5">
                  <span className="text-sm font-semibold text-slate-900">
                    {displayName}
                  </span>
                  <span className="text-xs font-normal text-slate-500">
                    {email}
                  </span>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link
                    to="/profile"
                    onClick={closeOnMobile}
                    className="flex items-center gap-2"
                  >
                    <User className="h-4 w-4" />
                    Profile
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link
                    to="/settings"
                    onClick={closeOnMobile}
                    className="flex items-center gap-2"
                  >
                    <Settings className="h-4 w-4" />
                    Settings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="destructive" onSelect={onLogout}>
                  <LogOut className="h-4 w-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  );
}

export function RootLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { profile, loading: profileLoading } = useProfile();
  const { currentUser, loading: authLoading, logout } = useAuth();
  const { removeGoal } = useGoals();
  const [pendingDelete, setPendingDelete] = React.useState<UserGoal | null>(
    null,
  );

  if (authLoading || profileLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500">
        Loading...
      </div>
    );
  }

  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }

  if (!profile) {
    return <Navigate to="/onboarding" replace />;
  }

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const handleConfirmDelete = () => {
    if (!pendingDelete) return;
    const wasViewingGoal = location.pathname.startsWith(
      `/career-goal/${pendingDelete.id}`,
    );
    removeGoal(pendingDelete.id);
    setPendingDelete(null);
    if (wasViewingGoal) {
      navigate("/", { replace: true });
    }
  };

  const displayName = profile.name?.trim() || currentUser.name || "You";

  return (
    <SidebarProvider>
      <AppSidebar
        displayName={displayName}
        email={currentUser.email}
        onLogout={handleLogout}
        onRequestDeleteGoal={setPendingDelete}
      />
      <SidebarInset className="bg-slate-50">
        <header className="sticky top-0 z-40 flex h-14 shrink-0 items-center gap-2 border-b border-slate-200/60 bg-white/90 px-4 backdrop-blur">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-1 h-5!" />
          <span className="text-sm font-semibold tracking-tight text-slate-950">
            AI Career Helper
          </span>
          <div className="ml-auto flex items-center gap-1">
            <NotificationsButton />
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:py-8">
          <Outlet />
        </main>
      </SidebarInset>

      <AlertDialog
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open) setPendingDelete(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-red-50 text-red-700">
                <AlertTriangle className="h-5 w-5" />
              </span>
              Delete this career goal?
            </AlertDialogTitle>
            <AlertDialogDescription>
              You're about to permanently delete{" "}
              <span className="font-semibold text-slate-900">
                {pendingDelete?.title}
              </span>
              . Your confidence quiz answers and progress for this goal will be
              lost. This can't be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep goal</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-red-600 text-white hover:bg-red-700 focus:ring-red-200"
            >
              Yes, delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <NotificationOrchestrator />
    </SidebarProvider>
  );
}
