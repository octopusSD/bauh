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

    def get_missing_packages(self, names: Set[str], mirror: str = None, in_analysis: Set[str] = None) -> List[Tuple[str, str]]:

        missing_names = pacman.check_missing(names)

        if missing_names:
            global_in_analysis = in_analysis if in_analysis else set()

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
                        global_in_analysis.add(dep[0])
            else:
                for missing in missing_names:
                    missing_root.append((missing, mirror))
                    global_in_analysis.add(missing)

            missing_sub = []
            for dep in missing_root:
                subdeps = self.aur_client.get_all_dependencies(dep[0]) if dep[1] == 'aur' else pacman.read_dependencies(dep[0])
                subdeps_not_analysed = {dep for dep in subdeps if dep not in global_in_analysis}

                if subdeps_not_analysed:
                    missing_subdeps = self.get_missing_packages(subdeps_not_analysed, in_analysis=global_in_analysis)

                    # checking if there is any unknown:
                    if missing_subdeps:
                        for subdep in missing_subdeps:
                            if not subdep[0]:
                                missing_sub.extend(missing_subdeps)
                                break

                        missing_sub.extend(missing_subdeps)

            return [*missing_sub, *missing_root]

    def get_missing_subdeps_of(self, names: Set[str], mirror: str) -> List[Tuple[str, str]]:
        missing = []
        for name in names:
            subdeps = self.aur_client.get_all_dependencies(name) if mirror == 'aur' else pacman.read_dependencies(name)

            if subdeps:
                missing_subdeps = self.get_missing_packages(subdeps, in_analysis={*names})

                if missing_subdeps:
                    missing.extend(missing_subdeps)

                    for subdep in missing_subdeps:  # checking if there is any unknown:
                        if not subdep[0]:
                            return missing

        return missing
