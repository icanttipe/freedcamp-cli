_freedcamp() {
  local cur prev cmd
  COMPREPLY=()
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"
  cmd="${COMP_WORDS[1]}"

  if [[ $COMP_CWORD -eq 1 ]]; then
    COMPREPLY=($(compgen -W "init projects tasks task create update complete delete raw --help --version" -- "$cur"))
    return
  fi

  case "$cmd" in
    tasks)
      if [[ $COMP_CWORD -eq 3 ]]; then
        COMPREPLY=($(compgen -W "--all" -- "$cur"))
      fi
      ;;
    create)
      case "$prev" in
        --priority)    COMPREPLY=($(compgen -W "0 1 2 3" -- "$cur"));;
        --status)      COMPREPLY=($(compgen -W "0 1 2" -- "$cur"));;
        -p|--project|-g|--group|-t|--title|-d|--desc|-a|--assign|--start|--due|--parent) ;;
        *)             COMPREPLY=($(compgen -W "-p --project -g --group -t --title -d --desc -a --assign --start --due --parent --priority --status" -- "$cur"));;
      esac
      ;;
    update)
      if [[ $COMP_CWORD -ge 3 ]]; then
        case "$prev" in
          -s|--status)   COMPREPLY=($(compgen -W "0 1 2" -- "$cur"));;
          --priority)    COMPREPLY=($(compgen -W "0 1 2 3" -- "$cur"));;
          -t|--title|-d|--desc|-a|--assign|--start|--due) ;;
          *)             COMPREPLY=($(compgen -W "-t --title -d --desc -s --status --start --due -a --assign --priority" -- "$cur"));;
        esac
      fi
      ;;
    raw)
      if [[ $COMP_CWORD -eq 2 ]]; then
        COMPREPLY=($(compgen -W "GET POST DELETE" -- "$cur"))
      fi
      ;;
  esac
}

complete -F _freedcamp freedcamp
