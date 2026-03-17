/**
 * In-browser Tomb of Horrors–style dungeon generator.
 * Outputs the same JSON shape as dnd_module generator for use in dm.html.
 */
(function (global) {
  'use strict';

  const WALL = '#';
  const FLOOR = '.';
  const ENTRANCE = 'E';
  const GOAL = 'G';

  const ROOM_TYPES = [
    'entrance', 'corridor', 'hall', 'chamber', 'prison', 'chapel',
    'throne_room', 'crypt', 'treasure_room', 'trap_room', 'puzzle_room', 'dead_end'
  ];

  const ROOM_NAMES = {
    entrance: ['False Entrance Tunnel', 'Entrance to the Tomb', 'Crawl Space'],
    corridor: ['Corridor', 'Passage', 'Winding Passage'],
    hall: ['Great Hall', 'Hall of Spheres', 'Columned Hall'],
    chamber: ['Chamber', 'Room', 'Cubicle'],
    prison: ['Forsaken Prison', 'Guard Room', 'Holding Cell'],
    chapel: ['Chapel of Evil', 'Shrine', 'Temple Area'],
    throne_room: ['Pillared Throne Room', 'Throne Room', 'Dais Chamber'],
    crypt: ['Crypt', 'Burial Vault', 'False Crypt'],
    treasure_room: ['Treasure Room', 'Hoard', 'False Treasure Room'],
    trap_room: ['Trapped Corridor', 'Deadly Gallery', 'Trap Room'],
    puzzle_room: ['Arch of Mist', 'Portal Chamber', 'Puzzle Room'],
    dead_end: ['Dead End', 'Blind Corridor', 'False Passage']
  };

  const ROOM_DESCRIPTIONS = {
    entrance: [
      'The corridor is of plain stone, roughly worked, dark and full of cobwebs. Daylight reveals a pair of doors at the end.',
      'Bright colors are visible even by torchlight—stones and pigments undimmed by time. A distinct path winds ahead.'
    ],
    corridor: [
      'A plain stone passageway; the walls are smooth and the floor is paved.',
      'Dust hangs in the air. Faint scratches mark the floor where others have passed.'
    ],
    hall: [
      'A great hall with inlaid tiles underfoot and painted figures on the walls—animals, glyphs, and humanoid shapes.',
      'Massive columns support the ceiling. The floor is mosaic; the walls show scenes of strange significance.'
    ],
    chamber: [
      'A smallish chamber with bare stone. No obvious exit save the way you came.',
      'Plain walls and a high ceiling. Something here feels watched.'
    ],
    prison: [
      'This miserable cubicle appears to have no means of egress. Levers protrude from one wall.',
      'A cell with no visible door. Detection magic reveals nothing—yet there are levers.'
    ],
    chapel: [
      'Scenes of life are painted on the walls, but the figures show rotting flesh and skeletal hands.',
      'Religious symbols of good alignment mix with depictions of decay. A mosaic path leads to the altar.'
    ],
    throne_room: [
      'Scores of massive columns fill the chamber. Each pillar radiates magic when detected.',
      'A huge dais supports an obsidian throne inlaid with silver and ivory.'
    ],
    crypt: [
      'A small burial vault with an arched ceiling. The center of the floor has a shallow depression.',
      'The end of the adventure—one way or another—is near. A crypt with a single notable feature.'
    ],
    treasure_room: [
      'An imposing chamber with a silvered ceiling. Statues of black iron stand in the corners.',
      'Treasure seems to await—but the room radiates anti-magic. Proceed with caution.'
    ],
    trap_room: [
      'The passage here is narrow. The floor shows slight irregularities.',
      'Something about this place sets the nerves on edge. Test each step.'
    ],
    puzzle_room: [
      'An archway blocks the path. Stones set into the frame glow when approached—yellow, blue, orange.',
      'The correct sequence of pressed stones will clear the way. Wrong choices lead elsewhere.'
    ],
    dead_end: [
      'The passage ends in solid stone. Or does it? Detection may reveal more.',
      'Dead end. The walls are featureless—or so they appear.'
    ]
  };

  const TRAP_KINDS = ['pit', 'sliding_block', 'spear', 'gas', 'crushing', 'teleport', 'spike_volley', 'poison_needle'];
  const TRAP_DAMAGE = {
    pit: '10\' pit, spikes (poison save)',
    sliding_block: 'Crushed; block seals passage.',
    spear: '2-16 (2d8) when door opened.',
    gas: 'Save vs poison or strength loss / sleep.',
    crushing: '10-100 (10d10) or squashed.',
    teleport: 'Teleported to another area.',
    spike_volley: '2-5 spikes, 1-6 each.',
    poison_needle: 'Poison (save or die).'
  };
  const CLUE_PHRASES = [
    'Go back to the tormentor or through the arch.',
    'Shun green if you can; night\'s good color is for those of great valor.',
    'If you find the false you find the true.',
    'The iron men of visage grim do more than meets the viewer\'s eye.',
    'Look low and high for gold, to hear a tale untold.',
    'Beware of trembling hands and what will maul.'
  ];

  function mulberry32(seed) {
    return function () {
      let t = seed += 0x6D2B79F5;
      t = Math.imul(t ^ t >>> 15, t | 1);
      t ^= t + Math.imul(t ^ t >>> 7, t | 61);
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }

  function gridEmpty(grid, r, c, h, w, margin) {
    const rows = grid.length, cols = grid[0].length;
    for (let rr = Math.max(0, r - margin); rr < Math.min(rows, r + h + margin); rr++) {
      for (let cc = Math.max(0, c - margin); cc < Math.min(cols, c + w + margin); cc++) {
        if (grid[rr][cc] !== WALL) return false;
      }
    }
    return true;
  }

  function carveRoom(grid, room, cellType) {
    for (let rr = room.row; rr < room.row + room.height; rr++) {
      for (let cc = room.col; cc < room.col + room.width; cc++) {
        if (rr >= 0 && rr < grid.length && cc >= 0 && cc < grid[0].length) {
          grid[rr][cc] = cellType;
        }
      }
    }
  }

  function roomCenter(room) {
    return [room.row + Math.floor(room.height / 2), room.col + Math.floor(room.width / 2)];
  }

  function carveCorridor(grid, r1, c1, r2, c2) {
    const rows = grid.length, cols = grid[0].length;
    let r = r1, c = c1;
    while (r !== r2) {
      if (r >= 0 && r < rows && c >= 0 && c < cols) grid[r][c] = FLOOR;
      r += r2 > r ? 1 : -1;
    }
    while (c !== c2) {
      if (r >= 0 && r < rows && c >= 0 && c < cols) grid[r][c] = FLOOR;
      c += c2 > c ? 1 : -1;
    }
    if (r >= 0 && r < rows && c >= 0 && c < cols) grid[r][c] = FLOOR;
  }

  function buildDungeon(height, width, minRooms, maxRooms, rng) {
    const grid = Array.from({ length: height }, () => Array(width).fill(WALL));
    const rooms = [];
    const count = Math.floor(rng() * (maxRooms - minRooms + 1)) + minRooms;
    const margin = 1;
    for (let i = 0; i < count * 3; i++) {
      if (rooms.length >= count) break;
      const h = Math.floor(rng() * 4) + 3;
      const w = Math.floor(rng() * 6) + 3;
      const r = Math.floor(rng() * (height - h - 2)) + 1;
      const c = Math.floor(rng() * (width - w - 2)) + 1;
      if (gridEmpty(grid, r, c, h, w, margin)) {
        rooms.push({
          id: 'area_' + (rooms.length + 1),
          row: r, col: c, height: h, width: w,
          room_type: 'chamber',
          connections: []
        });
        carveRoom(grid, rooms[rooms.length - 1]);
      }
    }
    for (let i = 1; i < rooms.length; i++) {
      const other = Math.floor(rng() * i);
      const [r1, c1] = roomCenter(rooms[i]);
      const [r2, c2] = roomCenter(rooms[other]);
      carveCorridor(grid, r1, c1, r2, c2);
      rooms[i].connections.push(rooms[other].id);
      rooms[other].connections.push(rooms[i].id);
    }
    return { grid, rooms };
  }

  function assignRoomTypes(rooms, entranceId, goalId) {
    rooms.forEach(room => {
      if (room.id === entranceId) room.room_type = 'entrance';
      else if (room.id === goalId) room.room_type = 'crypt';
      else if (room.connections.length === 1) {
        room.room_type = ['dead_end', 'trap_room', 'chamber'][Math.floor(Math.random() * 3)];
      } else if (room.connections.length >= 3) {
        room.room_type = ['hall', 'throne_room', 'chapel'][Math.floor(Math.random() * 3)];
      } else {
        room.room_type = ['corridor', 'chamber', 'puzzle_room', 'prison'][Math.floor(Math.random() * 4)];
      }
    });
  }

  function pick(arr, rng) {
    return arr[Math.floor(rng() * arr.length)];
  }

  function buildModule(seed) {
    const rng = seed != null ? mulberry32(seed) : () => Math.random();
    const height = 24, width = 32;
    const minRooms = 8, maxRooms = 16;
    const { grid, rooms } = buildDungeon(height, width, minRooms, maxRooms, rng);
    if (rooms.length === 0) {
      return {
        version: 'tomb-module-1.0',
        title: 'Generated Tomb of Horrors',
        legend: { title: '', backstory: 'The dungeon could not be generated.', locale_options: [], dm_notes: '' },
        map: { height, width, cells: [] },
        areas: [], traps: [], switches: [], clues: []
      };
    }
    const entranceId = rooms[0].id;
    const goalId = rooms[rooms.length - 1].id;
    assignRoomTypes(rooms, entranceId, goalId);
    const [er, ec] = roomCenter(rooms[0]);
    const [gr, gc] = roomCenter(rooms[rooms.length - 1]);
    grid[er][ec] = ENTRANCE;
    grid[gr][gc] = GOAL;

    const cells = [];
    for (let r = 0; r < height; r++) {
      for (let c = 0; c < width; c++) {
        cells.push({ row: r, col: c, cell_type: grid[r][c], area_id: null });
      }
    }

    const areas = rooms.map(room => {
      const names = ROOM_NAMES[room.room_type] || ROOM_NAMES.chamber;
      const descs = ROOM_DESCRIPTIONS[room.room_type] || ROOM_DESCRIPTIONS.chamber;
      return {
        id: room.id,
        position: { row: room.row, col: room.col },
        room_type: room.room_type,
        name: pick(names, rng),
        description: pick(descs, rng),
        doors: room.connections.map((conn, idx) => ({
          position: { row: room.row, col: room.col + idx },
          door_type: rng() < 0.2 ? 'secret' : rng() < 0.15 ? 'false' : 'closed',
          key_id: null,
          open_method: null,
          leads_to_area: conn
        })),
        traps: [],
        switches: [],
        clues: [],
        connections: room.connections
      };
    });

    const trapCandidates = areas.filter(a => a.id !== entranceId && a.id !== goalId && a.room_type !== 'entrance');
    const nTraps = Math.max(1, Math.floor(trapCandidates.length * 0.35));
    for (let i = 0; i < nTraps && i < trapCandidates.length; i++) {
      const area = trapCandidates[i];
      const kind = pick(TRAP_KINDS, rng);
      const trap = {
        position: { row: area.position.row + 1, col: area.position.col + 1 },
        kind,
        armed: true,
        disarm_switch_id: null,
        damage: TRAP_DAMAGE[kind] || 'Various.',
        save: null,
        description: ''
      };
      area.traps.push(trap);
    }

    const nClues = Math.max(1, Math.floor(areas.length * 0.25));
    const clueAreas = areas.slice().sort(() => rng() - 0.5).slice(0, nClues);
    const clues = [];
    clueAreas.forEach(area => {
      const text = pick(CLUE_PHRASES, rng);
      const clue = { area_id: area.id, format: 'riddle', text, hints_at: [] };
      area.clues.push(clue);
      clues.push(clue);
    });

    const allTraps = areas.flatMap(a => a.traps);

    const introVariants = [
      'The hill rises before you—low, flat-topped, its sides thick with weeds, thorns, and briars. Tales say the crypt lies beneath: traps, guardians, and treasures. You have found the place. The entrance is hidden; only a careful search will reveal it. What do you do?',
      'Before you, a low hill, bare and overgrown. The legends are clear: beneath it lies the crypt—traps and treasures both. You stand at the site. The way in is hidden. What do you do?',
      'A flat-topped mound rises from the ground, thorn and briar crowding its sides. This is the place from the tales: the crypt below, its traps and its hoard. The entrance is not obvious. What do you do?'
    ];
    const backstory = pick(introVariants, rng);

    return {
      version: 'tomb-module-1.0',
      title: 'Generated Tomb of Horrors',
      legend: {
        title: 'Generated Tomb of Horrors',
        backstory: backstory,
        locale_options: [
          'The highest hill on the plains',
          'An unmapped island in the great lake',
          'In the wastes of the desert',
          'At the border of the northern duchy',
          'Somewhere in the vast swamp',
          'On an island beyond the realm of the sea barons'
        ],
        dm_notes: 'This is a thinking person\'s module. Negotiation requires caution and observation. Read keyed areas as players arrive.'
      },
      map: { height, width, cells, entrance_area_id: entranceId, goal_area_id: goalId },
      areas,
      traps: allTraps,
      switches: [],
      clues,
      eval_hazards: allTraps.map(t => [t.position.row, t.position.col])
    };
  }

  global.generateDungeon = function (seed) {
    return buildModule(seed == null ? undefined : seed);
  };
})(typeof window !== 'undefined' ? window : this);
