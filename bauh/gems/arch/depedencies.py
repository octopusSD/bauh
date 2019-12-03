from threading import Thread
from typing import Set, List, Tuple

from bauh.gems.arch import pacman
from bauh.gems.arch.aur import AURClient


class DependenciesAnalyser:

    def __init__(self, aur_client: AURClient):
        self.aur_client = aur_client

    def _fill_mirror(self, name: str, output: List[Tuple[str, str]]):

        mirror = pacman.read_repository_from_info(name)

        if mirror:
            output.append((name, mirror))
            return

        guess = pacman.guess_repository(name)

        if guess:
            output.append(guess)
            return

        aur_info = self.aur_client.get_src_info(name)

        if aur_info:
            output.append((name, 'aur'))
            return

        output.append((name, ''))

    def get_missing_dependencies(self, names: Set[str], mirror: str = None) -> List[Tuple[str, str]]:

        missing_names = pacman.check_missing(names)

        if missing_names:
            missing_root = []
            threads = []

            if not mirror:
                for name in missing_names:
                    t = Thread(target=self._fill_mirror, args=(name, missing_root))
                    t.start()
                    threads.append(t)

                for t in threads:
                    t.join()

                threads.clear()

                # checking if there is any unknown dependency:
                for dep in missing_root:
                    if not dep[1]:
                        return missing_root
            else:
                for missing in missing_names:
                    missing_root.append((missing, mirror))

            missing_sub = []
            for dep in missing_root:
                subdeps = self.aur_client.get_all_dependencies(dep[0]) if dep[1] == 'aur' else pacman.read_dependencies(dep[0])

                if subdeps:
                    missing_subdeps = self.get_missing_dependencies(subdeps)

                    # checking if there is any unknown:
                    for dep in missing_subdeps:
                        if not dep[0]:
                            missing_sub.extend(missing_subdeps)
                            break

                    missing_sub.extend(missing_subdeps)

            return [*missing_sub, *missing_root]
