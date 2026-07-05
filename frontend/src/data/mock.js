// Placeholder data for Assistify OS

export const currentUser = {
  name: "Jordan Rivera",
  email: "jordan@assistify.io",
  role: "Founder",
  avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzZ8MHwxfHNlYXJjaHwxfHxwcm9mZXNzaW9uYWwlMjBoZWFkc2hvdCUyMHBvcnRyYWl0fGVufDB8fHx8MTc4MzE2NzAyNXww&ixlib=rb-4.1.0&q=85",
  plan: "Enterprise",
};

export const stats = [
  { label: "Total Revenue", value: "$284,320", change: "+18.2%", up: true, icon: "DollarSign" },
  { label: "Active Projects", value: "37", change: "+4", up: true, icon: "FolderKanban" },
  { label: "Clients", value: "128", change: "+12", up: true, icon: "Users" },
  { label: "AI Tasks Run", value: "9,412", change: "+1.2k", up: true, icon: "Bot" },
];

export const revenueData = [
  { month: "Jan", revenue: 18400, expenses: 9200 },
  { month: "Feb", revenue: 22100, expenses: 10400 },
  { month: "Mar", revenue: 19800, expenses: 11200 },
  { month: "Apr", revenue: 28600, expenses: 12800 },
  { month: "May", revenue: 34200, expenses: 14100 },
  { month: "Jun", revenue: 41800, expenses: 15600 },
  { month: "Jul", revenue: 38900, expenses: 15200 },
  { month: "Aug", revenue: 46700, expenses: 17300 },
];

export const projectStatusData = [
  { name: "In Progress", value: 14, color: "#8b5cf6" },
  { name: "Review", value: 8, color: "#22d3ee" },
  { name: "Completed", value: 11, color: "#34d399" },
  { name: "Blocked", value: 4, color: "#f87171" },
];

export const agentActivityData = [
  { day: "Mon", runs: 320 },
  { day: "Tue", runs: 480 },
  { day: "Wed", runs: 390 },
  { day: "Thu", runs: 620 },
  { day: "Fri", runs: 710 },
  { day: "Sat", runs: 280 },
  { day: "Sun", runs: 190 },
];

export const clients = [
  { id: 1, name: "Northwind Labs", contact: "Ava Mitchell", email: "ava@northwind.co", value: "$48,200", status: "Active", projects: 4, avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzZ8MHwxfHNlYXJjaHwzfHxwcm9mZXNzaW9uYWwlMjBoZWFkc2hvdCUyMHBvcnRyYWl0fGVufDB8fHx8MTc4MzE2NzAyNXww&ixlib=rb-4.1.0&q=85" },
  { id: 2, name: "Vertex Studio", contact: "Marcus Lee", email: "marcus@vertex.io", value: "$31,900", status: "Active", projects: 2, avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzZ8MHwxfHNlYXJjaHwxfHxwcm9mZXNzaW9uYWwlMjBoZWFkc2hvdCUyMHBvcnRyYWl0fGVufDB8fHx8MTc4MzE2NzAyNXww&ixlib=rb-4.1.0&q=85" },
  { id: 3, name: "Halcyon Group", contact: "Priya Nair", email: "priya@halcyon.com", value: "$62,400", status: "Active", projects: 5, avatar: "https://images.pexels.com/photos/31869537/pexels-photo-31869537.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940" },
  { id: 4, name: "Cobalt Ventures", contact: "Sam Okoro", email: "sam@cobalt.vc", value: "$19,750", status: "Lead", projects: 1, avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzZ8MHwxfHNlYXJjaHwzfHxwcm9mZXNzaW9uYWwlMjBoZWFkc2hvdCUyMHBvcnRyYWl0fGVufDB8fHx8MTc4MzE2NzAyNXww&ixlib=rb-4.1.0&q=85" },
  { id: 5, name: "Lumen Analytics", contact: "Elena Rossi", email: "elena@lumen.ai", value: "$54,100", status: "Active", projects: 3, avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzZ8MHwxfHNlYXJjaHwxfHxwcm9mZXNzaW9uYWwlMjBoZWFkc2hvdCUyMHBvcnRyYWl0fGVufDB8fHx8MTc4MzE2NzAyNXww&ixlib=rb-4.1.0&q=85" },
  { id: 6, name: "Apex Digital", contact: "Tom Becker", email: "tom@apex.dev", value: "$27,300", status: "Churned", projects: 0, avatar: "https://images.pexels.com/photos/31869537/pexels-photo-31869537.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940" },
];

export const projects = [
  { id: 1, name: "Brand Redesign", client: "Northwind Labs", progress: 72, status: "In Progress", due: "Aug 24", members: 4 },
  { id: 2, name: "Mobile App v2", client: "Vertex Studio", progress: 45, status: "In Progress", due: "Sep 02", members: 6 },
  { id: 3, name: "Data Migration", client: "Lumen Analytics", progress: 90, status: "Review", due: "Aug 18", members: 3 },
  { id: 4, name: "Q3 Campaign", client: "Halcyon Group", progress: 100, status: "Completed", due: "Aug 10", members: 5 },
  { id: 5, name: "API Integration", client: "Cobalt Ventures", progress: 20, status: "Blocked", due: "Sep 15", members: 2 },
  { id: 6, name: "Content Strategy", client: "Halcyon Group", progress: 60, status: "In Progress", due: "Aug 30", members: 3 },
];

export const tasks = [
  { id: 1, title: "Finalize proposal for Northwind", priority: "High", done: false, due: "Today", project: "Brand Redesign" },
  { id: 2, title: "Review mobile app wireframes", priority: "Medium", done: false, due: "Tomorrow", project: "Mobile App v2" },
  { id: 3, title: "Send invoice to Halcyon Group", priority: "High", done: false, due: "Aug 16", project: "Q3 Campaign" },
  { id: 4, title: "Sync with Cobalt on API blockers", priority: "High", done: false, due: "Aug 17", project: "API Integration" },
  { id: 5, title: "Draft weekly client update", priority: "Low", done: true, due: "Aug 14", project: "Content Strategy" },
  { id: 6, title: "QA data migration batch 3", priority: "Medium", done: false, due: "Aug 18", project: "Data Migration" },
  { id: 7, title: "Prepare Q3 analytics report", priority: "Medium", done: true, due: "Aug 12", project: "Q3 Campaign" },
];

export const proposals = [
  { id: 1, title: "Northwind Brand System", client: "Northwind Labs", amount: "$24,000", status: "Sent", date: "Aug 12" },
  { id: 2, title: "Vertex Mobile Scope", client: "Vertex Studio", amount: "$41,500", status: "Draft", date: "Aug 10" },
  { id: 3, title: "Lumen Analytics Retainer", client: "Lumen Analytics", amount: "$8,000/mo", status: "Accepted", date: "Aug 08" },
  { id: 4, title: "Halcyon Growth Package", client: "Halcyon Group", amount: "$62,000", status: "Sent", date: "Aug 05" },
  { id: 5, title: "Cobalt API Consulting", client: "Cobalt Ventures", amount: "$15,000", status: "Rejected", date: "Aug 01" },
];

export const documents = [
  { id: 1, name: "Master Services Agreement.pdf", type: "PDF", size: "2.4 MB", client: "Northwind Labs", date: "Aug 14" },
  { id: 2, name: "Brand Guidelines.fig", type: "Figma", size: "18 MB", client: "Northwind Labs", date: "Aug 13" },
  { id: 3, name: "Q3 Roadmap.docx", type: "Doc", size: "640 KB", client: "Internal", date: "Aug 12" },
  { id: 4, name: "Financial Model.xlsx", type: "Sheet", size: "1.1 MB", client: "Internal", date: "Aug 11" },
  { id: 5, name: "Vertex Contract.pdf", type: "PDF", size: "980 KB", client: "Vertex Studio", date: "Aug 09" },
  { id: 6, name: "Campaign Assets.zip", type: "Archive", size: "44 MB", client: "Halcyon Group", date: "Aug 07" },
  { id: 7, name: "Discovery Notes.md", type: "Doc", size: "22 KB", client: "Cobalt Ventures", date: "Aug 05" },
  { id: 8, name: "Analytics Export.csv", type: "Sheet", size: "310 KB", client: "Lumen Analytics", date: "Aug 03" },
];

export const notifications = [
  { id: 1, text: "Halcyon Group accepted your proposal", time: "2m ago", type: "success" },
  { id: 2, text: "New task assigned: QA data migration", time: "1h ago", type: "info" },
  { id: 3, text: "Cobalt Ventures project is blocked", time: "3h ago", type: "warning" },
  { id: 4, text: "Sales Strategist drafted 3 cold emails", time: "5h ago", type: "info" },
];

export const trafficData = [
  { source: "Direct", visits: 4200 },
  { source: "Referral", visits: 3100 },
  { source: "Organic", visits: 5400 },
  { source: "Social", visits: 2200 },
  { source: "Email", visits: 1800 },
];
