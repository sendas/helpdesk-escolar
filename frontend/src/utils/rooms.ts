// Rooms shown grouped by kind (Sala de aula, Sala TIC, Laboratório…), in the order of the agrupamento's list
export function groupRooms<T extends { kind: string }>(rooms: T[]): { kind: string; rooms: T[] }[] {
  const groups: { kind: string; rooms: T[] }[] = []
  for (const r of rooms) {
    let g = groups.find((x) => x.kind === r.kind)
    if (!g) groups.push((g = { kind: r.kind, rooms: [] }))
    g.rooms.push(r)
  }
  return groups
}
